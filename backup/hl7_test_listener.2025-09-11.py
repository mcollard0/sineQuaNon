#!/usr/bin/env python3
"""
Simple HL7 Test Listener
========================
A basic HL7 listener that accepts MLLP-framed messages and sends ACK responses.
Perfect for testing our funny HL7 messages!

Author: AI Assistant
Date: 2025-09-04
"""

import socket
import datetime
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_timestamp():
    """Generate HL7 timestamp format: YYYYMMDDHHMMSS"""
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def create_ack_message(original_message):
    """Create an ACK message for the received HL7 message"""
    lines = original_message.strip().split('\n')
    msh_line = lines[0] if lines else ""
    
    # Extract control ID from MSH segment (field 10)
    if msh_line.startswith('MSH'):
        fields = msh_line.split('|')
        control_id = fields[10] if len(fields) > 10 else "UNKNOWN"
    else:
        control_id = "UNKNOWN"
    
    timestamp = get_timestamp()
    
    ack = f"""MSH|^~\\&|LAUGH_TRACK|FUNNY_FARM|SENDER|COMEDY_DEPT|{timestamp}||ACK^A01^ACK|ACK{timestamp[-6:]}|P|2.2|||||||
MSA|AA|{control_id}|MESSAGE RECEIVED WITH GIGGLES|
NTE|1||Dr. Giggles says: Message received loud and clear!
NTE|2||The Funny Farm Asylum appreciates your humorous transmission"""
    
    return ack

def handle_client(client_socket, client_address):
    """Handle a client connection"""
    logger.info(f"🎭 New connection from {client_address}")
    
    try:
        while True:
            # Receive data
            data = client_socket.recv(4096)
            if not data:
                break
                
            logger.info(f"📨 Received {len(data)} bytes from {client_address}")
            
            # Remove MLLP framing
            start_block = b'\\x0b'
            end_block = b'\\x1c'
            carriage_return = b'\\r'
            
            # Strip MLLP framing
            clean_data = data
            if clean_data.startswith(start_block):
                clean_data = clean_data[1:]
            if clean_data.endswith(end_block + carriage_return):
                clean_data = clean_data[:-2]
            elif clean_data.endswith(carriage_return):
                clean_data = clean_data[:-1]
            
            message = clean_data.decode('utf-8')
            logger.info(f"📋 Decoded message:\\n{message}")
            
            # Determine message type
            lines = message.split('\\n')
            msh_line = lines[0] if lines else ""
            
            if 'ADT^A01' in msh_line:
                print("\\n🏥 ADT ADMISSION MESSAGE RECEIVED!")
                print("Matt Knee-Slapper Jr. has been admitted to the Funny Farm!")
            elif 'ORU^R01' in msh_line:
                print("\\n🔬 ORU LAB RESULTS RECEIVED!")
                print("Matt's humor levels are critically low - emergency comedy required!")
            
            # Create and send ACK
            ack_message = create_ack_message(message)
            wrapped_ack = start_block + ack_message.encode('utf-8') + end_block + carriage_return
            
            client_socket.send(wrapped_ack)
            logger.info(f"✅ ACK sent to {client_address}")
            
    except Exception as e:
        logger.error(f"💥 Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        logger.info(f"🔌 Connection to {client_address} closed")

def start_hl7_listener(host='localhost', port=2575):
    """Start the HL7 listener server"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        
        print(f"🎪 Funny Farm Asylum HL7 Listener started on {host}:{port}")
        print("🏥 Dr. Giggles is ready to receive patients!")
        print("Press Ctrl+C to stop the listener\\n")
        
        while True:
            client_socket, client_address = server_socket.accept()
            # Handle each client in a separate thread
            client_thread = threading.Thread(
                target=handle_client, 
                args=(client_socket, client_address)
            )
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\\n\\n🛑 Dr. Giggles is taking a break!")
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"💥 Server error: {e}")
    finally:
        server_socket.close()
        print("🔌 Funny Farm Asylum HL7 Listener stopped")

if __name__ == "__main__":
    start_hl7_listener()
