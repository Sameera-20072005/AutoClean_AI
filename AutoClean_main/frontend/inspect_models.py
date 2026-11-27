
from pathlib import Path
import joblib
import sklearn

model_dir = Path("backend/app/models/models")

print("scikit-learn version:", sklearn.__version__)

for path in model_dir.glob("*.joblib"):
    print("\n" + "=" * 50)
    print("MODEL:", path.name)

    try:
        model = joblib.load(path)

        print("Type:", type(model).__name__)
        print("Input features:", getattr(model, "n_features_in_", None))
        print("Class IDs:", getattr(model, "classes_", None))
        print("Feature importances:", getattr(model, "feature_importances_", None))

        if hasattr(model, "get_params"):
            print("Parameters:", model.get_params())

    except Exception as error:
        print("Could not load:", type(error).__name__, str(error))
