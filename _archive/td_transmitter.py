"""
TouchDesigner Data Transmitter
Supports multiple protocols: OSC, TCP, UDP, WebSocket
"""

import json
import socket
import time
from typing import List, Dict, Any
import threading

# OSC support
try:
    from pythonosc import udp_client
    OSC_AVAILABLE = True
except ImportError:
    print("Warning: python-osc not installed. Install with: pip install python-osc")
    OSC_AVAILABLE = False

# WebSocket support
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class TouchDesignerTransmitter:
    """Transmit person detection data to TouchDesigner"""
    
    def __init__(self, protocol='osc', host='127.0.0.1', port=7000, camera_id=None):
        """
        Initialize transmitter
        
        Args:
            protocol: 'osc', 'tcp', 'udp', 'websocket', or 'json_file'
            host: TouchDesigner host IP
            port: TouchDesigner port (OSC: 7000, TCP: 8080, etc.)
            camera_id: Camera identifier (e.g., 1, 2, 3) for multi-camera setup
        """
        self.protocol = protocol
        self.host = host
        self.port = port
        self.camera_id = camera_id
        self.client = None
        
        # Initialize based on protocol
        if protocol == 'osc':
            self._init_osc()
        elif protocol == 'tcp':
            self._init_tcp()
        elif protocol == 'udp':
            self._init_udp()
        elif protocol == 'websocket':
            self._init_websocket()
        elif protocol == 'json_file':
            self._init_json_file()
        else:
            raise ValueError(f"Unknown protocol: {protocol}")
        
        print(f"TouchDesigner transmitter initialized: {protocol}://{host}:{port}")
    
    def _init_osc(self):
        """Initialize OSC client"""
        if not OSC_AVAILABLE:
            raise ImportError("python-osc not installed. Install with: pip install python-osc")
        self.client = udp_client.SimpleUDPClient(self.host, self.port)
        print("  ✓ OSC client ready")
    
    def _init_tcp(self):
        """Initialize TCP socket"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
            print("  ✓ TCP socket connected")
        except ConnectionRefusedError:
            print(f"  ⚠ TCP connection failed. Make sure TouchDesigner is listening on {self.host}:{self.port}")
            self.sock = None
    
    def _init_udp(self):
        """Initialize UDP socket"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("  ✓ UDP socket ready")
    
    def _init_websocket(self):
        """Initialize WebSocket client"""
        if not WEBSOCKET_AVAILABLE:
            raise ImportError("websocket-client not installed. Install with: pip install websocket-client")
        ws_url = f"ws://{self.host}:{self.port}"
        self.client = websocket.create_connection(ws_url)
        print("  ✓ WebSocket connected")
    
    def _init_json_file(self):
        """Initialize JSON file output"""
        self.json_file = "td_data.json"
        print(f"  ✓ JSON file output: {self.json_file}")
    
    def quantize_data(self, results: List[Dict]) -> Dict[str, Any]:
        """
        Quantize all data for transmission
        
        Returns:
            Quantized data dictionary
        """
        quantized = {
            'timestamp': time.time(),
            'person_count': len(results),
            'persons': []
        }
        
        # Add camera_id if set (for multi-camera)
        if self.camera_id is not None:
            quantized['camera_id'] = self.camera_id
        
        for r in results:
            person_data = {
                'id': r.get('person_id', 0),
                
                # Bounding box (normalized 0-1)
                'bbox': {
                    'x1': r['bbox'][0] / 1280.0 if len(r['bbox']) > 0 else 0.0,
                    'y1': r['bbox'][1] / 720.0 if len(r['bbox']) > 1 else 0.0,
                    'x2': r['bbox'][2] / 1280.0 if len(r['bbox']) > 2 else 0.0,
                    'y2': r['bbox'][3] / 720.0 if len(r['bbox']) > 3 else 0.0,
                },
                
                # Face attributes
                'face': {},
                'emotion': None,
                'emotion_conf': 0.0,
                
                # Body attributes
                'body_type': {},
                
                # Clothing
                'clothing': {},
                
                # Keypoints (normalized 0-1)
                'keypoints': []
            }
            
            # Face data
            if r.get('face'):
                face = r['face']
                person_data['face'] = {
                    'age': face.get('smoothed_age', face.get('age', 0)),
                    'age_normalized': min(face.get('smoothed_age', face.get('age', 0)) / 100.0, 1.0)
                }
            
            # Emotion (Label Encoding)
            if r.get('emotion'):
                emotion_map = {
                    'happy': 0, 'sad': 1, 'angry': 2, 'surprise': 3,
                    'fear': 4, 'disgust': 5, 'neutral': 6
                }
                person_data['emotion'] = emotion_map.get(r['emotion'].lower(), 6)
                person_data['emotion_conf'] = r.get('emotion_conf', 0.0)
            
            # Body type (Label Encoding)
            if r.get('body_type'):
                bt = r['body_type']
                build_map = {'athletic': 0, 'slim': 1, 'stocky': 2, 'average': 3}
                shape_map = {'v-shape': 0, 'a-shape': 1, 'rectangle': 2}
                
                person_data['body_type'] = {
                    'build': build_map.get(bt.get('build', 'average').lower(), 3),
                    'shape': shape_map.get(bt.get('shape', 'rectangle').lower(), 2)
                }
            
            # Clothing (Label Encoding)
            if r.get('clothing'):
                clothing = r['clothing']
                
                # Clothing type
                upper_type_map = {'t-shirt': 0, 'shirt': 1, 'top': 2, 'dress': 3}
                lower_type_map = {'pants': 0, 'shorts': 1, 'bottom': 2}
                
                upper_type = 2  # default: Top
                lower_type = 2  # default: Bottom
                
                if clothing.get('type'):
                    ct = clothing['type']
                    if ct.get('upper'):
                        upper_type = upper_type_map.get(ct['upper'].lower(), 2)
                    if ct.get('lower'):
                        lower_type = lower_type_map.get(ct['lower'].lower(), 2)
                
                # Clothing color
                color_map = {
                    'red': 0, 'blue': 1, 'green': 2, 'yellow': 3,
                    'black': 4, 'white': 5, 'gray': 6, 'mixed': 7
                }
                
                upper_color = 7  # default: Mixed
                lower_color = 7
                
                if clothing.get('upper_color'):
                    upper_color = color_map.get(clothing['upper_color'].lower(), 7)
                if clothing.get('lower_color'):
                    lower_color = color_map.get(clothing['lower_color'].lower(), 7)
                
                person_data['clothing'] = {
                    'upper_type': upper_type,
                    'upper_color': upper_color,
                    'lower_type': lower_type,
                    'lower_color': lower_color
                }
            
            # Keypoints (normalized coordinates + confidence)
            if r.get('keypoints') is not None:
                keypoints = r['keypoints']
                for kpt in keypoints:
                    if len(kpt) >= 3:
                        person_data['keypoints'].append({
                            'x': kpt[0] / 1280.0,  # Normalized to [0, 1]
                            'y': kpt[1] / 720.0,
                            'confidence': kpt[2]
                        })
            
            quantized['persons'].append(person_data)
        
        return quantized
    
    def send_osc(self, data: Dict):
        """Send data via OSC"""
        if not self.client:
            return
        
        # OSC address pattern: /camera{id}/person/{id}/attribute or /person/{id}/attribute
        if self.camera_id is not None:
            base_address = f"/camera{self.camera_id}/person"
        else:
            base_address = "/person"
        
        # Send person count
        self.client.send_message(f"{base_address}/count", data['person_count'])
        
        # Debug: Print person count
        if data['person_count'] > 1:
            print(f"[DEBUG] Sending {data['person_count']} persons to TouchDesigner")
        
        # Send each person's data
        for person in data['persons']:
            pid = person['id']
            addr = f"{base_address}/{pid}"
            
            # Debug: Print each person being sent
            if data['person_count'] > 1:
                print(f"[DEBUG] Sending Person {pid}...")
            
            # Face data
            if person.get('face'):
                self.client.send_message(f"{addr}/age", person['face']['age'])
                self.client.send_message(f"{addr}/age_norm", person['face']['age_normalized'])
            
            # Emotion
            if person.get('emotion') is not None:
                self.client.send_message(f"{addr}/emotion", person['emotion'])
                self.client.send_message(f"{addr}/emotion_conf", person['emotion_conf'])
            
            # Body type
            if person.get('body_type'):
                self.client.send_message(f"{addr}/build", person['body_type']['build'])
                self.client.send_message(f"{addr}/shape", person['body_type']['shape'])
            
            # Clothing
            if person.get('clothing'):
                c = person['clothing']
                self.client.send_message(f"{addr}/upper_type", c['upper_type'])
                self.client.send_message(f"{addr}/upper_color", c['upper_color'])
                self.client.send_message(f"{addr}/lower_type", c['lower_type'])
                self.client.send_message(f"{addr}/lower_color", c['lower_color'])
            
            # Bounding box
            bbox = person['bbox']
            self.client.send_message(f"{addr}/bbox/x1", bbox['x1'])
            self.client.send_message(f"{addr}/bbox/y1", bbox['y1'])
            self.client.send_message(f"{addr}/bbox/x2", bbox['x2'])
            self.client.send_message(f"{addr}/bbox/y2", bbox['y2'])
            
            # Keypoints (send as arrays)
            if person.get('keypoints'):
                kpts = person['keypoints']
                # Send keypoint positions as arrays
                x_coords = [kpt['x'] for kpt in kpts]
                y_coords = [kpt['y'] for kpt in kpts]
                confs = [kpt['confidence'] for kpt in kpts]
                
                self.client.send_message(f"{addr}/keypoints/x", x_coords)
                self.client.send_message(f"{addr}/keypoints/y", y_coords)
                self.client.send_message(f"{addr}/keypoints/conf", confs)
            
            # Small delay between persons to ensure TouchDesigner receives all data
            if data['person_count'] > 1:
                time.sleep(0.02)  # 20ms delay between persons (increased for reliability)
    
    def send_tcp(self, data: Dict):
        """Send data via TCP"""
        if not self.sock:
            return
        
        try:
            # Convert NumPy types to Python native types
            data = self._convert_numpy_types(data)
            json_str = json.dumps(data, separators=(',', ':'))
            message = json_str.encode('utf-8') + b'\n'
            self.sock.sendall(message)
        except Exception as e:
            print(f"TCP send error: {e}")
    
    def send_udp(self, data: Dict):
        """Send data via UDP (split into multiple packets for multiple persons)"""
        try:
            # Convert NumPy types to Python native types
            data = self._convert_numpy_types(data)
            
            # Send person count first
            count_msg = json.dumps({'person_count': data['person_count']}, separators=(',', ':'))
            self.sock.sendto(count_msg.encode('utf-8'), (self.host, self.port))
            
            # Send each person as a separate packet
            for person in data['persons']:
                person_msg = json.dumps({'person': person}, separators=(',', ':'))
                message = person_msg.encode('utf-8')
                
                # Check packet size
                if len(message) > 1400:
                    # Packet too large, remove keypoints detail
                    person_light = person.copy()
                    if 'keypoints' in person_light and len(person_light['keypoints']) > 0:
                        # Only send first/last keypoint as reference
                        person_light['keypoints'] = [
                            person_light['keypoints'][0],
                            person_light['keypoints'][-1]
                        ]
                    person_msg = json.dumps({'person': person_light}, separators=(',', ':'))
                    message = person_msg.encode('utf-8')
                
                self.sock.sendto(message, (self.host, self.port))
                
        except Exception as e:
            print(f"UDP send error: {e}")
    
    def send_websocket(self, data: Dict):
        """Send data via WebSocket"""
        if not self.client:
            return
        
        try:
            # Convert NumPy types to Python native types
            data = self._convert_numpy_types(data)
            json_str = json.dumps(data, separators=(',', ':'))
            self.client.send(json_str)
        except Exception as e:
            print(f"WebSocket send error: {e}")
    
    def send_json_file(self, data: Dict):
        """Write data to JSON file"""
        try:
            # Convert NumPy types to Python native types
            data = self._convert_numpy_types(data)
            with open(self.json_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"JSON file write error: {e}")
    
    def _convert_numpy_types(self, obj):
        """
        Convert NumPy types to Python native types for JSON serialization
        """
        import numpy as np
        
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.ndarray):
            return self._convert_numpy_types(obj.tolist())
        elif isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64,
                             np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        else:
            return obj
    
    def transmit(self, results: List[Dict]):
        """
        Main transmit function - quantizes and sends data
        
        Args:
            results: List of person detection results from process_frame()
        """
        # Quantize data
        quantized = self.quantize_data(results)
        
        # Send based on protocol
        if self.protocol == 'osc':
            self.send_osc(quantized)
        elif self.protocol == 'tcp':
            self.send_tcp(quantized)
        elif self.protocol == 'udp':
            self.send_udp(quantized)
        elif self.protocol == 'websocket':
            self.send_websocket(quantized)
        elif self.protocol == 'json_file':
            self.send_json_file(quantized)
    
    def close(self):
        """Close connections"""
        if self.protocol == 'tcp' and self.sock:
            self.sock.close()
        elif self.protocol == 'udp' and self.sock:
            self.sock.close()
        elif self.protocol == 'websocket' and self.client:
            self.client.close()


# Example usage
if __name__ == "__main__":
    # Example results data
    example_results = [
        {
            'person_id': 1,
            'bbox': (100, 200, 300, 600),
            'face': {'age': 25, 'smoothed_age': 25},
            'emotion': 'happy',
            'emotion_conf': 0.95,
            'body_type': {'build': 'Athletic', 'shape': 'V-Shape'},
            'clothing': {
                'type': {'upper': 'T-shirt', 'lower': 'Pants'},
                'upper_color': 'Red',
                'lower_color': 'Blue'
            },
            'keypoints': [[100, 200, 0.9], [150, 250, 0.8], ...]
        }
    ]
    
    # Initialize transmitter
    transmitter = TouchDesignerTransmitter(protocol='osc', port=7000)
    
    # Transmit data
    transmitter.transmit(example_results)
    
    # Close when done
    transmitter.close()

