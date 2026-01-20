import mediapipe as mp
try:
    print("Files in mp:", dir(mp))
    print("Does mp have solutions?", hasattr(mp, 'solutions'))
    import mediapipe.python.solutions as solutions
    print("Can import mediapipe.python.solutions directly")
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Error: {e}")
