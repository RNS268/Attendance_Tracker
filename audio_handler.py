import threading
import time
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Callable
from collections import deque

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: pyttsx3 not available. Using print-based audio callback.")

# ============================================================================
# Configuration Constants
# ============================================================================

AUDIO_COOLDOWN_GLOBAL = 2.0      # Seconds between audio playbacks globally
AUDIO_COOLDOWN_PER_PERSON = 5.0  # Seconds before same person can trigger audio again
SESSION_TIMEOUT = 300.0          # Seconds of inactivity before person cleanup
REAPPEAR_THRESHOLD = 2.0         # Seconds to consider person as reappearing

# ============================================================================
# State Machine Definition
# ============================================================================

class PersonState(Enum):
    """States for attendance tracking per person."""
    NEW = "NEW"           # First detection in session
    MARKING = "MARKING"   # Attendance being marked by external system
    MARKED = "MARKED"     # Attendance successfully marked
    IGNORED = "IGNORED"   # Person already marked, no further audio

# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class PersonRecord:
    """Tracks state and timing for a single person."""
    person_id: str
    name: str
    state: PersonState = PersonState.NEW
    last_audio_time: float = 0.0
    last_seen_time: float = 0.0
    audio_lock_until: float = 0.0
    has_triggered_ignored_audio: bool = False

# ============================================================================
# Main Audio Handler Class
# ============================================================================

class AudioHandler:
    """
    Handles audio playback and state management for attendance system.
    Manages per-person state transitions and enforces audio rules.
    
    Features:
    - Thread-safe state management
    - Sequential audio playback (no overlaps)
    - Per-person and global cooldowns
    - Automatic session cleanup
    - Flexible audio backend (pyttsx3 or custom callback)
    """
    
    def __init__(self, audio_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize AudioHandler.
        
        Args:
            audio_callback: Optional function to call with audio text to play.
                          Signature: callback(audio_text: str)
                          If None, uses pyttsx3 if available, else prints.
        """
        # Setup audio backend
        if audio_callback:
            self.audio_callback = audio_callback
        elif TTS_AVAILABLE:
            self._tts_engine = pyttsx3.init()
            self._tts_lock = threading.Lock()
            self.audio_callback = self._tts_callback
        else:
            self.audio_callback = self._print_callback
        
        # Session state
        self.session_active = False
        self.global_cooldown_until = 0.0
        
        # Core data structures
        self.people: Dict[str, PersonRecord] = {}
        self.audio_queue = deque()
        self.audio_queue_lock = threading.Lock()
        self.data_lock = threading.RLock()
        
        # Background threads
        self.audio_thread_running = True
        self.audio_thread = threading.Thread(
            target=self._process_audio_queue, 
            daemon=True,
            name="AudioQueueProcessor"
        )
        self.audio_thread.start()
        
        self.cleanup_thread = threading.Thread(
            target=self._session_cleanup_loop, 
            daemon=True,
            name="SessionCleanup"
        )
        self.cleanup_thread.start()
        
        print("AudioHandler initialized successfully")
    
    # ========================================================================
    # Audio Backend Callbacks
    # ========================================================================
    
    def _tts_callback(self, text: str) -> None:
        """Built-in TTS callback using pyttsx3."""
        with self._tts_lock:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
    
    def _print_callback(self, text: str) -> None:
        """Fallback callback that prints audio text."""
        print(f"🔊 AUDIO: {text}")
    
    # ========================================================================
    # Public Session Management
    # ========================================================================
    
    def start_session(self) -> None:
        """Begin a new session, resetting all states."""
        with self.data_lock:
            self.session_active = True
            self.people.clear()
            self.global_cooldown_until = 0.0
            
            with self.audio_queue_lock:
                self.audio_queue.clear()
            
            print("✓ Session started: All states reset")
    
    def end_session(self) -> None:
        """End current session, reset all states and locks."""
        with self.data_lock:
            self.session_active = False
            self.people.clear()
            self.global_cooldown_until = 0.0
            
            with self.audio_queue_lock:
                self.audio_queue.clear()
            
            print("✓ Session ended: All states cleared")
    
    # ========================================================================
    # Core Processing Method
    # ========================================================================
    
    def process_person(
        self, 
        person_id: str, 
        person_name: str, 
        is_recognized: bool, 
        attendance_marked: bool
    ) -> None:
        """
        Process a recognized person. Main entry point for face recognition system.
        
        Args:
            person_id: Unique identifier for the person
            person_name: Display name for audio messages
            is_recognized: True if face is recognized (else ignore)
            attendance_marked: True if external system marked attendance
        """
        if not self.session_active:
            return
            
        if not is_recognized:
            return
        
        current_time = time.time()
        
        with self.data_lock:
            # Get or create person record
            person = self._get_or_create_person(person_id, person_name, current_time)
            
            # Check if this is a reappearance (person was absent, now returned)
            time_since_last_seen = current_time - person.last_seen_time
            is_reappearance = time_since_last_seen > REAPPEAR_THRESHOLD
            
            # Update last seen time
            person.last_seen_time = current_time
            
            # Check per-person audio lock
            if current_time < person.audio_lock_until:
                return
            
            # Store previous state for transition detection
            previous_state = person.state
            
            # Apply state transitions
            self._apply_state_transitions(person, attendance_marked, is_reappearance)
            
            # Trigger audio only if state changed
            if person.state != previous_state:
                self._trigger_audio_for_transition(person, previous_state, current_time)
    
    # ========================================================================
    # State Transition Logic
    # ========================================================================
    
    def _apply_state_transitions(
        self, 
        person: PersonRecord, 
        attendance_marked: bool,
        is_reappearance: bool
    ) -> None:
        """Apply state machine transitions based on current state and inputs."""
        if person.state == PersonState.NEW:
            # First detection in session
            person.state = PersonState.MARKING
            
        elif person.state == PersonState.MARKING and attendance_marked:
            # External system confirmed attendance
            person.state = PersonState.MARKED
            
        elif person.state == PersonState.MARKED and is_reappearance:
            # Person reappears after being marked
            person.state = PersonState.IGNORED
            
        # IGNORED state is absorbing (stays IGNORED until session reset)
    
    def _trigger_audio_for_transition(
        self, 
        person: PersonRecord, 
        previous_state: PersonState,
        current_time: float
    ) -> None:
        """Queue appropriate audio based on state transition."""
        
        # Define audio messages for each transition
        audio_messages = {
            (PersonState.NEW, PersonState.MARKING): "Marking attendance",
            (PersonState.MARKING, PersonState.MARKED): f"Greetings {person.name}",
            (PersonState.MARKED, PersonState.IGNORED): 
                f"{person.name}, your attendance is already marked. Only once per session."
        }
        
        transition = (previous_state, person.state)
        
        if transition in audio_messages:
            audio_text = audio_messages[transition]
            
            # Special handling: IGNORED audio plays only once per person per session
            if person.state == PersonState.IGNORED:
                if person.has_triggered_ignored_audio:
                    return
                person.has_triggered_ignored_audio = True
            
            # Apply per-person audio lock
            person.audio_lock_until = current_time + AUDIO_COOLDOWN_PER_PERSON
            
            # Queue audio for playback
            self._queue_audio(audio_text, current_time)
    
    # ========================================================================
    # Audio Queue Management
    # ========================================================================
    
    def _queue_audio(self, audio_text: str, current_time: float) -> None:
        """Add audio to queue for serialized playback."""
        with self.audio_queue_lock:
            self.audio_queue.append((audio_text, current_time))
    
    def _process_audio_queue(self) -> None:
        """Background thread to process audio queue with global cooldown."""
        while self.audio_thread_running:
            time.sleep(0.05)  # 50ms polling interval
            
            with self.audio_queue_lock:
                if not self.audio_queue:
                    continue
                
                # Peek at next audio
                audio_text, queue_time = self.audio_queue[0]
                current_time = time.time()
                
                # Check global cooldown
                if current_time < self.global_cooldown_until:
                    continue
                
                # Remove from queue and prepare to play
                self.audio_queue.popleft()
            
            # Play audio outside lock to avoid blocking queue operations
            try:
                self.audio_callback(audio_text)
            except Exception as e:
                print(f"Error playing audio: {e}")
            
            # Update global cooldown
            with self.data_lock:
                self.global_cooldown_until = time.time() + AUDIO_COOLDOWN_GLOBAL
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _get_or_create_person(
        self, 
        person_id: str, 
        person_name: str, 
        current_time: float
    ) -> PersonRecord:
        """Get existing person or create new record."""
        if person_id not in self.people:
            self.people[person_id] = PersonRecord(
                person_id=person_id,
                name=person_name,
                state=PersonState.NEW,
                last_seen_time=current_time
            )
        return self.people[person_id]
    
    def get_person_state(self, person_id: str) -> Optional[PersonState]:
        """Get current state of a person (for debugging/monitoring)."""
        with self.data_lock:
            person = self.people.get(person_id)
            return person.state if person else None
    
    def get_all_states(self) -> Dict[str, str]:
        """Get all person states as strings (for debugging/monitoring)."""
        with self.data_lock:
            return {pid: p.state.value for pid, p in self.people.items()}
    
    def get_session_info(self) -> Dict:
        """Get comprehensive session information."""
        with self.data_lock:
            return {
                "session_active": self.session_active,
                "total_people": len(self.people),
                "queue_size": len(self.audio_queue),
                "states": self.get_all_states()
            }
    
    # ========================================================================
    # Session Cleanup
    # ========================================================================
    
    def _session_cleanup_loop(self) -> None:
        """Background thread to clean up old person records."""
        while True:
            time.sleep(60.0)  # Check every minute
            
            if not self.session_active:
                continue
            
            current_time = time.time()
            cutoff_time = current_time - SESSION_TIMEOUT
            
            with self.data_lock:
                to_remove = [
                    pid for pid, person in self.people.items()
                    if person.last_seen_time < cutoff_time
                ]
                
                for pid in to_remove:
                    del self.people[pid]
                
                if to_remove:
                    print(f"🗑️  Session cleanup: Removed {len(to_remove)} inactive persons")
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    def shutdown(self) -> None:
        """Clean shutdown of audio handler."""
        print("Shutting down AudioHandler...")
        self.audio_thread_running = False
        self.audio_thread.join(timeout=2.0)
        self.end_session()
        print("AudioHandler shutdown complete")

# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example 1: Using default audio backend
    print("\n=== Example 1: Default Backend ===")
    handler1 = AudioHandler()
    handler1.start_session()
    
    # Simulate person detection
    handler1.process_person("001", "Alice", True, False)
    time.sleep(0.5)
    handler1.process_person("001", "Alice", True, True)  # Attendance marked
    time.sleep(3)
    handler1.process_person("001", "Alice", True, True)  # Reappearance
    
    handler1.end_session()
    
    # Example 2: Using custom callback
    print("\n=== Example 2: Custom Callback ===")
    def custom_audio(text: str):
        print(f">>> CUSTOM AUDIO: {text}")
    
    handler2 = AudioHandler(audio_callback=custom_audio)
    handler2.start_session()
    
    handler2.process_person("002", "Bob", True, False)
    time.sleep(0.5)
    handler2.process_person("002", "Bob", True, True)
    
    time.sleep(5)  # Wait for audio to complete
    
    print("\nSession Info:", handler2.get_session_info())
    
    handler2.shutdown()
    handler1.shutdown()