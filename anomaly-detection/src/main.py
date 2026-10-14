import json
import os
from detector import BaselineAnomalyDetector

def main():
    # 1. Load the simulated telemetry data
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_telemetry.json')
    with open(data_path, 'r') as f:
        telemetry_stream = json.load(f)

    # 2. Extract historical "normal" values (first 4 points) to train the baseline
    historical_data = [item['value'] for item in telemetry_stream[:-1]]
    
    # 3. Initialize and train the detector
    detector = BaselineAnomalyDetector(threshold_z=3.0)
    detector.fit(historical_data)
    print("Baseline trained successfully.")

    # 4. Simulate a new incoming telemetry point (the last point - spike to 3200ms)
    incoming_point = telemetry_stream[-1]
    print(f"\nAnalyzing new telemetry point: {incoming_point}")

    # 5. Run detection and output the structured event
    result = detector.detect(incoming_point)
    
    print("\n--- ANOMALY EVENT OUTPUT ---")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
