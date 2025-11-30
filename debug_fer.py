import fer
print(f"FER package file: {fer.__file__}")
print(f"FER package dir: {dir(fer)}")
try:
    from fer import FER
    print("Successfully imported FER")
except ImportError as e:
    print(f"Failed to import FER: {e}")

