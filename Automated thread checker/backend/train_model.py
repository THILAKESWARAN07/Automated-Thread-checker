"""Train a small CNN for GOOD vs DEFECT thread classification."""

from __future__ import annotations

from pathlib import Path

import tensorflow as tf

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "data" / "dataset"
MODEL_PATH = BASE_DIR / "models" / "thread_model.h5"
IMAGE_SIZE = (128, 128)
BATCH_SIZE = 32
EPOCHS = 10


def build_model() -> tf.keras.Model:
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], 3)),
            tf.keras.layers.Conv2D(32, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(64, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(128, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.Precision(), tf.keras.metrics.Recall()],
    )
    return model


def main() -> None:
    if not DATASET_DIR.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_DIR}. Create GOOD and DEFECT folders first."
        )

    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR,
        validation_split=0.2,
        subset="training",
        seed=123,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATASET_DIR,
        validation_split=0.2,
        subset="validation",
        seed=123,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
    )

    class_names = train_ds.class_names
    print("Classes:", class_names)

    normalization_layer = tf.keras.layers.Rescaling(1.0 / 255)
    data_augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.06),
            tf.keras.layers.RandomZoom(0.08),
        ]
    )

    train_ds = train_ds.map(lambda x, y: (data_augmentation(normalization_layer(x)), y))
    val_ds = val_ds.map(lambda x, y: (normalization_layer(x), y))

    train_ds = train_ds.prefetch(buffer_size=tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(buffer_size=tf.data.AUTOTUNE)

    model = build_model()
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True)
    ]

    model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_PATH)
    print(f"Saved trained model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
