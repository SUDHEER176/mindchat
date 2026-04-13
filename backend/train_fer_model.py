"""
Train a CNN on the FER2013 dataset (fer2013.csv) and save the model.

Usage:
    python train_fer_model.py

The trained model will be saved as:
    backend/fer_model.h5   (Keras HDF5 format)

FER2013 emotion label map:
    0 = Angry
    1 = Disgust
    2 = Fear
    3 = Happy
    4 = Sad
    5 = Surprise
    6 = Neutral
"""

import os
import sys
import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Locate the CSV
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Accept CSV path as first CLI arg, otherwise look in common spots
if len(sys.argv) > 1:
    CSV_PATH = sys.argv[1]
else:
    candidates = [
        os.path.join(BASE_DIR, "data", "fer2013.csv"),
        os.path.join(BASE_DIR, "__pycache__", "fer2013.csv"),
        os.path.join(BASE_DIR, "fer2013.csv"),
        r"C:\Users\sudhe\Downloads\fer2013.csv\fer2013.csv",
    ]
    CSV_PATH = next((p for p in candidates if os.path.exists(p)), None)

if CSV_PATH is None or not os.path.exists(CSV_PATH):
    print("[FER] ERROR: fer2013.csv not found. Pass the path as an argument:")
    print("       python train_fer_model.py path/to/fer2013.csv")
    sys.exit(1)

MODEL_OUT = os.path.join(BASE_DIR, "fer_model.h5")

print(f"[FER] Using CSV : {CSV_PATH}")
print(f"[FER] Output    : {MODEL_OUT}")

# ------------------------------------------------------------------
# Load CSV
# ------------------------------------------------------------------
print("[FER] Loading CSV …")
df = pd.read_csv(CSV_PATH)
print(f"[FER] Rows loaded: {len(df):,}")

# ------------------------------------------------------------------
# Parse pixels
# ------------------------------------------------------------------
def parse_pixels(pixel_str):
    return np.array(pixel_str.split(), dtype=np.float32)

print("[FER] Parsing pixel data …")
X = np.stack(df["pixels"].apply(parse_pixels).values)   # (N, 2304)
y = df["emotion"].values.astype(np.int32)                # (N,)

# Normalise to [0, 1] and reshape to (N, 48, 48, 1)
X = X / 255.0
X = X.reshape(-1, 48, 48, 1)

# Train / validation split (keep original Usage column if present)
if "Usage" in df.columns:
    train_mask = df["Usage"] == "Training"
    val_mask   = df["Usage"].isin(["PublicTest", "PrivateTest"])
    X_train, y_train = X[train_mask], y[train_mask]
    X_val,   y_val   = X[val_mask],   y[val_mask]
else:
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

print(f"[FER] Train samples: {len(X_train):,}  |  Val samples: {len(X_val):,}")

NUM_CLASSES = 7

# ------------------------------------------------------------------
# Build CNN
# ------------------------------------------------------------------
print("[FER] Building model …")
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
except ImportError:
    try:
        import keras
        from keras import layers
        import tensorflow as tf
    except ImportError:
        print("[FER] ERROR: TensorFlow / Keras not installed.")
        print("       pip install tf-keras tensorflow")
        sys.exit(1)

def build_model(num_classes=7):
    inputs = keras.Input(shape=(48, 48, 1))

    # Block 1
    x = layers.Conv2D(64, 3, padding="same", activation="relu")(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(64, 3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D(2)(x)
    x = layers.Dropout(0.25)(x)

    # Block 2
    x = layers.Conv2D(128, 3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(128, 3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D(2)(x)
    x = layers.Dropout(0.25)(x)

    # Block 3
    x = layers.Conv2D(256, 3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(256, 3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D(2)(x)
    x = layers.Dropout(0.25)(x)

    # Classifier head
    x = layers.Flatten()(x)
    x = layers.Dense(512, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs, name="fer_cnn")
    return model

model = build_model(NUM_CLASSES)
model.summary()

# ------------------------------------------------------------------
# Compile & train
# ------------------------------------------------------------------
model.compile(
    optimizer=keras.optimizers.Adam(1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

callbacks = [
    keras.callbacks.ModelCheckpoint(
        MODEL_OUT,
        monitor="val_accuracy",
        save_best_only=True,
        verbose=1,
    ),
    keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=5,
        min_lr=1e-6,
        verbose=1,
    ),
    keras.callbacks.EarlyStopping(
        monitor="val_accuracy",
        patience=10,
        restore_best_weights=True,
        verbose=1,
    ),
]

# Data augmentation (on-the-fly)
datagen = keras.preprocessing.image.ImageDataGenerator(
    rotation_range=10,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True,
    zoom_range=0.1,
)
datagen.fit(X_train)

EPOCHS     = 50
BATCH_SIZE = 64

print(f"[FER] Training for up to {EPOCHS} epochs …")
history = model.fit(
    datagen.flow(X_train, y_train, batch_size=BATCH_SIZE),
    epochs=EPOCHS,
    validation_data=(X_val, y_val),
    callbacks=callbacks,
    verbose=1,
)

# ------------------------------------------------------------------
# Evaluate & save
# ------------------------------------------------------------------
val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
print(f"\n[FER] ✅ Training complete!")
print(f"[FER]    Val accuracy : {val_acc * 100:.2f}%")
print(f"[FER]    Val loss     : {val_loss:.4f}")
print(f"[FER]    Model saved  : {MODEL_OUT}")
