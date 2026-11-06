"""Single source of truth for revision-2 native render delivery."""
WIDTH = 1920
HEIGHT = 1080
FPS = 60
SECONDS = 20
FRAME_COUNT = FPS * SECONDS
CHUNK_SIZE = 12
CHUNK_COUNT = (FRAME_COUNT + CHUNK_SIZE - 1) // CHUNK_SIZE
REVISION = 2

# Expensive full animation stays gated until the revised lighting/flight is approved.
FULL_RENDER_APPROVED = False
