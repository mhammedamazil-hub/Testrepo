"""Single source of truth for revision-2 native render delivery."""
WIDTH = 1920
HEIGHT = 1080
FPS = 60
SECONDS = 20
FRAME_COUNT = FPS * SECONDS
CHUNK_SIZE = 12
CHUNK_COUNT = (FRAME_COUNT + CHUNK_SIZE - 1) // CHUNK_SIZE
REVISION = 2

# Final creative choices confirmed; opening/mid/ending look tests passed.
# Post-render native movie/temporal verification is still required.
FULL_RENDER_APPROVED = True
