"""
AI Learning System for Suno Studio Pro

Learns user preferences over time using local machine learning.
All data stays on the user's computer - no cloud uploads.
"""

import pickle
import numpy as np
import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not installed. AI learning will be limited.")


class UserPreferenceLearner:
    def __init__(self, model_path=None):
        """
        Initialize the AI learning system
        
        Args:
            model_path: Path to save/load the trained model
        """
        if model_path is None:
            # Default path in user's home directory
            model_dir = Path.home() / '.suno-studio' / 'models'
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / 'user_model.pkl'
        
        self.model_path = Path(model_path)
        self.training_data = []
        self.feature_scaler = StandardScaler() if HAS_SKLEARN else None
        
        # Load existing model or initialize new one
        self.model = self._load_or_create_model()
        
        # Statistics for debugging/monitoring
        self.stats = {
            "total_sessions": 0,
            "training_samples": 0,
            "last_trained": None,
            "prediction_accuracy": None
        }
        
        # Load existing stats if available
        stats_path = self.model_path.parent / 'learning_stats.json'
        if stats_path.exists():
            try:
                with open(stats_path, 'r') as f:
                    self.stats.update(json.load(f))
            except:
                pass
    
    def _load_or_create_model(self):
        """Load existing model or create a new one"""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                if isinstance(model_data, dict) and 'model' in model_data:
                    model = model_data['model']
                    if 'training_data' in model_data:
                        self.training_data = model_data['training_data']
                    if 'feature_scaler' in model_data and HAS_SKLEARN:
                        self.feature_scaler = model_data['feature_scaler']
                    return model
                else:
                    # Old format or corrupted
                    return self._create_new_model()
            except Exception as e:
                print(f"Error loading model: {e}")
                return self._create_new_model()
        else:
            return self._create_new_model()
    
    def _create_new_model(self):
        """Create a new model instance"""
        if HAS_SKLEARN:
            return RandomForestRegressor(
                n_estimators=50,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
        else:
            return None
    
    def extract_features(self, audio_metadata):
        """
        Extract features from audio metadata for prediction
        
        Args:
            audio_metadata: Dictionary with audio analysis results
            
        Returns:
            numpy array of features
        """
        features = []
        
        # Basic audio features
        features.append(audio_metadata.get("bpm", 120))
        features.append(audio_metadata.get("key", 0))  # Numeric key (0-11)
        features.append(audio_metadata.get("loudness_lufs", -20))
        features.append(audio_metadata.get("duration_seconds", 180))
        
        # Spectral features
        spectral_centroid = audio_metadata.get("spectral_centroid", 1000)
        features.append(spectral_centroid)
        
        # Frequency balance
        balance = audio_metadata.get("frequency_balance", {})
        features.append(balance.get("low_percent", 0.3))
        features.append(balance.get("mid_percent", 0.4))
        features.append(balance.get("high_percent", 0.3))
        
        # Dynamic range
        features.append(audio_metadata.get("dynamic_range_db", 10))
        
        # Genre encoding (one-hot inspired)
        genre = audio_metadata.get("genre", "unknown").lower()
        genre_encoding = {
            "electronic": 0, "edm": 0,
            "synthwave": 1, "vaporwave": 2,
            "house": 3, "techno": 3,
            "hiphop": 4, "rap": 4,
            "pop": 5, "rock": 6,
            "ambient": 7, "chill": 7
        }
        features.append(genre_encoding.get(genre, 8))  # 8 = other
        
        # Has vocals
        features.append(1 if audio_metadata.get("has_vocals", False) else 0)
        
        # Time of day (circadian encoding)
        hour = datetime.now().hour
        features.append(np.sin(2 * np.pi * hour / 24))
        features.append(np.cos(2 * np.pi * hour / 24))
        
        # Day of week
        day_of_week = datetime.now().weekday()
        features.append(np.sin(2 * np.pi * day_of_week / 7))
        features.append(np.cos(2 * np.pi * day_of_week / 7))
        
        return np.array(features, dtype=np.float32)
    
    def extract_targets(self, user_settings):
        """
        Extract target values from user settings
        
        Args:
            user_settings: Dictionary of user-chosen settings
            
        Returns:
            numpy array of target values
        """
        targets = []
        
        # Processing intensity
        targets.append(user_settings.get("artifact_intensity", 0.5))
        
        # Mastering parameters
        targets.append(user_settings.get("mastering_intensity", 1.0))
        
        # EQ preferences (simplified)
        bass_boost = user_settings.get("bass_boost", 0.0)
        targets.append(bass_boost)
        
        treble_boost = user_settings.get("treble_boost", 0.0)
        targets.append(treble_boost)
        
        # Loudness target
        target_lufs = user_settings.get("target_lufs", -14)
        targets.append(target_lufs)
        
        # Stereo width preference
        stereo_width = user_settings.get("stereo_width", 1.0)
        targets.append(stereo_width)
        
        # Reverb amount
        reverb_amount = user_settings.get("reverb_amount", 0.0)
        targets.append(reverb_amount)
        
        return np.array(targets, dtype=np.float32)
    
    def learn_from_session(self, audio_metadata, user_settings):
        """
        Learn from a user's processing session
        
        Args:
            audio_metadata: Audio analysis results
            user_settings: Settings chosen by user
        """
        if self.model is None:
            return
        
        try:
            # Extract features and targets
            features = self.extract_features(audio_metadata)
            targets = self.extract_targets(user_settings)
            
            # Add to training data
            self.training_data.append((features, targets))
            
            # Update statistics
            self.stats["total_sessions"] += 1
            self.stats["training_samples"] = len(self.training_data)
            self.stats["last_trained"] = datetime.now().isoformat()
            
            # Retrain if enough samples
            if len(self.training_data) >= 10:
                self._retrain_model()
            
            # Save stats
            self._save_stats()
            
        except Exception as e:
            print(f"Error learning from session: {e}")
    
    def _retrain_model(self):
        """Retrain the model with accumulated training data"""
        if not self.training_data or self.model is None:
            return
        
        try:
            # Prepare training data
            X = np.array([d[0] for d in self.training_data])
            y = np.array([d[1] for d in self.training_data])
            
            # Scale features if scaler available
            if self.feature_scaler is not None:
                X = self.feature_scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X, y)
            
            # Calculate prediction accuracy (simplified)
            predictions = self.model.predict(X)
            mse = np.mean((predictions - y) ** 2)
            self.stats["prediction_accuracy"] = 1.0 / (1.0 + mse)  # Inverse of MSE
            
            # Save model
            self._save_model()
            
            print(f"Model retrained with {len(self.training_data)} samples")
            
        except Exception as e:
            print(f"Error retraining model: {e}")
    
    def predict_optimal_settings(self, audio_metadata, confidence_threshold=0.7):
        """
        Predict optimal settings for a given audio file
        
        Args:
            audio_metadata: Audio analysis results
            confidence_threshold: Minimum confidence to return predictions
            
        Returns:
            Dictionary of predicted settings, or None if not confident
        """
        if self.model is None or len(self.training_data) < 5:
            return None
        
        try:
            # Extract features
            features = self.extract_features(audio_metadata)
            
            # Scale features if scaler available
            if self.feature_scaler is not None:
                features = features.reshape(1, -1)
                features = self.feature_scaler.transform(features)
            else:
                features = features.reshape(1, -1)
            
            # Predict
            prediction = self.model.predict(features)[0]
            
            # Convert prediction to settings dictionary
            settings = {
                "artifact_intensity": float(prediction[0]),
                "mastering_intensity": float(prediction[1]),
                "bass_boost": float(prediction[2]),
                "treble_boost": float(prediction[3]),
                "target_lufs": float(prediction[4]),
                "stereo_width": float(prediction[5]),
                "reverb_amount": float(prediction[6]),
            }
            
            # Calculate confidence based on training data size and variance
            confidence = min(1.0, len(self.training_data) / 50.0)  # More data = more confidence
            
            if self.stats.get("prediction_accuracy"):
                confidence *= self.stats["prediction_accuracy"]
            
            settings["confidence"] = confidence
            settings["training_samples"] = len(self.training_data)
            
            if confidence >= confidence_threshold:
                settings["source"] = "ai_learning"
                return settings
            else:
                # Return settings with low confidence warning
                settings["source"] = "ai_learning_low_confidence"
                return settings
                
        except Exception as e:
            print(f"Error predicting settings: {e}")
            return None
    
    def get_statistics(self):
        """Get learning statistics"""
        return self.stats.copy()
    
    def reset_learning(self):
        """Reset all learning data"""
        self.training_data = []
        self.model = self._create_new_model()
        self.stats = {
            "total_sessions": 0,
            "training_samples": 0,
            "last_trained": None,
            "prediction_accuracy": None
        }
        self._save_model()
        self._save_stats()
        print("AI learning reset")
    
    def export_learning_data(self, export_path):
        """Export learning data for analysis or backup"""
        export_data = {
            "training_data": [
                {
                    "features": features.tolist(),
                    "targets": targets.tolist()
                }
                for features, targets in self.training_data
            ],
            "statistics": self.stats,
            "export_date": datetime.now().isoformat()
        }
        
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return export_path
    
    def import_learning_data(self, import_path):
        """Import learning data from backup"""
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            # Convert back to numpy arrays
            self.training_data = []
            for item in import_data.get("training_data", []):
                features = np.array(item["features"], dtype=np.float32)
                targets = np.array(item["targets"], dtype=np.float32)
                self.training_data.append((features, targets))
            
            # Update statistics
            self.stats.update(import_data.get("statistics", {}))
            
            # Retrain model with imported data
            if self.training_data:
                self._retrain_model()
            
            print(f"Imported {len(self.training_data)} learning samples")
            return True
            
        except Exception as e:
            print(f"Error importing learning data: {e}")
            return False
    
    def _save_model(self):
        """Save model to disk"""
        try:
            model_data = {
                'model': self.model,
                'training_data': self.training_data,
                'feature_scaler': self.feature_scaler,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
        except Exception as e:
            print(f"Error saving model: {e}")
    
    def _save_stats(self):
        """Save statistics to disk"""
        try:
            stats_path = self.model_path.parent / 'learning_stats.json'
            with open(stats_path, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")


class SimpleRuleBasedLearner:
    """
    Fallback learner when scikit-learn is not available
    Uses simple rule-based learning instead of ML
    """
    
    def __init__(self, data_path=None):
        if data_path is None:
            data_dir = Path.home() / '.suno-studio' / 'simple_learning'
            data_dir.mkdir(parents=True, exist_ok=True)
            data_path = data_dir / 'preferences.json'
        
        self.data_path = Path(data_path)
        self.preferences = self._load_preferences()
    
    def _load_preferences(self):
        """Load preferences from disk"""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default preferences structure
        return {
            "genre_preferences": {},
            "time_preferences": {},
            "recent_settings": [],
            "session_count": 0
        }
    
    def learn_from_session(self, audio_metadata, user_settings):
        """Learn from session using simple rules"""
        genre = audio_metadata.get("genre", "unknown")
        
        # Update genre preferences
        if genre not in self.preferences["genre_preferences"]:
            self.preferences["genre_preferences"][genre] = []
        
        self.preferences["genre_preferences"][genre].append({
            "settings": user_settings,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only recent entries
        for genre in self.preferences["genre_preferences"]:
            entries = self.preferences["genre_preferences"][genre]
            if len(entries) > 20:  # Keep last 20 entries per genre
                self.preferences["genre_preferences"][genre] = entries[-20:]
        
        # Update session count
        self.preferences["session_count"] += 1
        
        # Save to disk
        self._save_preferences()
    
    def predict_optimal_settings(self, audio_metadata):
        """Predict settings based on genre patterns"""
        genre = audio_metadata.get("genre", "unknown")
        
        if genre in self.preferences["genre_preferences"]:
            entries = self.preferences["genre_preferences"][genre]
            
            if entries:
                # Average settings from recent entries
                recent_entries = entries[-5:]  # Last 5 entries
                
                # Simple averaging
                avg_settings = {}
                settings_keys = set()
                for entry in recent_entries:
                    settings_keys.update(entry["settings"].keys())
                
                for key in settings_keys:
                    values = [e["settings"].get(key, 0) for e in recent_entries if key in e["settings"]]
                    if values:
                        if isinstance(values[0], (int, float)):
                            avg_settings[key] = sum(values) / len(values)
                        else:
                            # For non-numeric, use most common
                            from collections import Counter
                            avg_settings[key] = Counter(values).most_common(1)[0][0]
                
                avg_settings["source"] = "simple_learning"
                avg_settings["confidence"] = min(1.0, len(entries) / 10.0)
                return avg_settings
        
        return None
    
    def _save_preferences(self):
        """Save preferences to disk"""
        try:
            with open(self.data_path, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")


def test_ai_learner():
    """Test the AI learning system"""
    print("Testing AI Learner...")
    
    # Create test metadata
    test_metadata = {
        "bpm": 128,
        "key": 5,  # F
        "loudness_lufs": -18.5,
        "duration_seconds": 215,
        "spectral_centroid": 1200,
        "frequency_balance": {
            "low_percent": 0.35,
            "mid_percent": 0.40,
            "high_percent": 0.25
        },
        "dynamic_range_db": 12.5,
        "genre": "electronic",
        "has_vocals": True
    }
    
    # Test settings
    test_settings = {
        "artifact_intensity": 0.7,
        "mastering_intensity": 0.8,
        "bass_boost": 2.5,
        "treble_boost": 1.0,
        "target_lufs": -14,
        "stereo_width": 1.2,
        "reverb_amount": 0.1
    }
    
    # Test with proper learner if sklearn available
    if HAS_SKLEARN:
        print("Testing with scikit-learn RandomForest...")
        learner = UserPreferenceLearner()
        
        # Learn from multiple sessions
        for i in range(15):
            # Slightly vary settings for different "sessions"
            varied_settings = test_settings.copy()
            varied_settings["artifact_intensity"] = 0.5 + (i * 0.02)
            learner.learn_from_session(test_metadata, varied_settings)
        
        # Get predictions
        predictions = learner.predict_optimal_settings(test_metadata)
        if predictions:
            print(f"Predictions: {predictions}")
            print(f"Confidence: {predictions.get('confidence', 0):.2f}")
        
        stats = learner.get_statistics()
        print(f"Statistics: {stats}")
        
    else:
        print("Testing with simple rule-based learner...")
        learner = SimpleRuleBasedLearner()
        
        for i in range(10):
            varied_settings = test_settings.copy()
            varied_settings["artifact_intensity"] = 0.5 + (i * 0.03)
            learner.learn_from_session(test_metadata, varied_settings)
        
        predictions = learner.predict_optimal_settings(test_metadata)
        if predictions:
            print(f"Predictions: {predictions}")
    
    print("AI Learner tests complete!")


if __name__ == "__main__":
    test_ai_learner()