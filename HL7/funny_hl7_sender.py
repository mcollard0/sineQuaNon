#!/usr/bin/env python3
"""
Funny HL7 2.2 Message Sender
============================
Sends humorous ADT and ORU messages for Matt's admission to Funny Farm Asylum
for his funny bone procedure.

Author: AI Assistant
Date: 2025-09-04
"""

import socket
import datetime
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_timestamp():
    """Generate HL7 timestamp format: YYYYMMDDHHMMSS"""
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def build_adt_message():
    """
    Build a humorous ADT^A01 (Admit) message for Matt's funny bone procedure
    """
    timestamp = get_timestamp()
    
    message = f"""MSH|^~\\&|FUNNY_FARM|ASYLUM_DEPT|ADT_SYS|LAUGH_TRACK|{timestamp}||ADT^A01^ADT_A01|MSG{timestamp[-6:]}|P|2.2|||||||
EVN||{timestamp}|||DR.CHUCKLE^GIGGLES^LAUGH^MD|||
PID|1||123456789^^^FUNNY_FARM^MR||KNEE^MATT^SLAPPER^JR||19900401|M||C|123 CHUCKLE STREET^^GIGGLETOWN^HA^12345^USA||(555)HAH-AHAH||(555)LOL-ROFL||S||987654321|||||||||||||||
NK1|1|KNEE^PATELLA^||456 BONE AVENUE^^JOINTVILLE^HA^54321^USA||(555)HIP-BONE||M|||||||||||||||||||
PV1|1|I|WARD^101^BED^1^A|||DR.CHUCKLE^GIGGLES^LAUGH^MD^||SURGERY|||A|||DR.CHUCKLE^GIGGLES^LAUGH^MD^|INP|VIP||19||||||||||||||||||A|||{timestamp}||||||||
PV2||EMERGENCY^FUNNY_BONE_FRACTURE^LAUGHTER_INDUCED|||||||||||||||||||||||N|A|||||||||||||
DG1|1||ACUTE.HUMERUS.DEFICIENCY^ACUTE HUMERUS DEFICIENCY - CHRONIC INABILITY TO LAUGH AT OWN JOKES|ACUTE HUMERUS DEFICIENCY|{timestamp}|||W|
PR1|1||FUNNY.BONE.RECON^FUNNY BONE RECONSTRUCTION WITH COMEDY IMPLANT|FUNNY BONE RECONSTRUCTION|{timestamp}|||120|MIN|DR.CHUCKLE^GIGGLES^LAUGH^MD^|
NTE|1||Patient admitted after severe case of unfunniness
NTE|2||Symptoms include: Dead pan delivery and inability to appreciate puns
NTE|3||Treatment plan: Emergency humor infusion and funny bone transplant
NTE|4||Prognosis: Expected to be knee-slapping good after procedure"""
    
    return message

def build_oru_message():
    """
    Build a humorous ORU^R01 (Lab Results) message for Matt's funny bone tests
    """
    timestamp = get_timestamp()
    observation_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    message = f"""MSH|^~\\&|LAB_GIGGLES|FUNNY_FARM|ORU_SYS|LAUGH_TRACK|{timestamp}||ORU^R01^ORU_R01|MSG{timestamp[-6:]}|P|2.2|||||||
PID|1||123456789^^^FUNNY_FARM^MR||KNEE^MATT^SLAPPER^JR||19900401|M||C|123 CHUCKLE STREET^^GIGGLETOWN^HA^12345^USA||(555)HAH-AHAH||(555)LOL-ROFL||S||987654321|||||||||||||||
PV1|1|I|WARD^101^BED^1^A|||DR.CHUCKLE^GIGGLES^LAUGH^MD^||SURGERY|||A|||DR.CHUCKLE^GIGGLES^LAUGH^MD^|INP|VIP||19||||||||||||||||||A|||{timestamp}||||||||
OBR|1|ORD{timestamp[-8:]}|LAB{timestamp[-6:]}|FUNNY^BONE^PANEL|||{observation_time}||||||||DR.CHUCKLE^GIGGLES^LAUGH^MD^||||||||{timestamp}||F|||||||||||||||||||
OBX|1|NM|HUMOR^LEVEL|1|2|LOL/dL|7-10|L|||F|||{observation_time}|COMEDY_LAB^DR.WITTY^BONES|||
OBX|2|NM|SARCASM^SATURATION|1|98|%|10-95|H|||F|||{observation_time}|COMEDY_LAB^DR.WITTY^BONES|||
OBX|3|NM|PUN^TOLERANCE|1|0.1|GROAN/JOKE|1.0-5.0|L|||F|||{observation_time}|COMEDY_LAB^DR.WITTY^BONES|||
OBX|4|NM|FUNNY^BONE^DENSITY|1|0.001|g/cm3|0.5-1.5|L|||F|||{observation_time}|COMEDY_LAB^DR.WITTY^BONES|||
OBX|5|TX|JOKE^COMPREHENSION|1|SEVERELY IMPAIRED - PATIENT EXPLAINS EVERY JOKE||||||F|||{observation_time}|COMEDY_LAB^DR.WITTY^BONES|||
OBX|6|TX|LAUGHTER^FREQUENCY|1|0 CHUCKLES PER HOUR||||||F|||{observation_time}|COMEDY_LAB^DR.WITTY^BONES|||
NTE|1||CRITICAL: Patient has lost all sense of humor
NTE|2||Recommend STAT stand-up comedy infusion
NTE|3||Consider emergency dad joke therapy
NTE|4||Warning: Patient may be contagiously serious"""
    
    return message

def send_hl7_message(message, host='localhost', port=2575, timeout=10):
    """
    Send an HL7 message using MLLP framing over TCP
    
    Args:
        message (str): The HL7 message to send
        host (str): Target hostname
        port (int): Target port
        timeout (int): Socket timeout in seconds
    
    Returns:
        str: ACK response if received, None otherwise
    """
    # MLLP framing: Start Block (VT) + Message + End Block (FS) + Carriage Return
    start_block = b'\x0b'  # VT (Vertical Tab)
    end_block = b'\x1c'    # FS (File Separator)
    carriage_return = b'\r' # CR
    
    # Wrap the message
    wrapped_message = start_block + message.encode('utf-8') + end_block + carriage_return
    
    sock = None
    try:
        # Create socket and connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        logger.info(f"🏥 Connecting to HL7 listener at {host}:{port}...")
        sock.connect((host, port))
        logger.info("✅ Connected successfully!")
        
        # Send the wrapped message
        logger.info(f"📤 Sending message ({len(wrapped_message)} bytes)...")
        sock.send(wrapped_message)
        logger.info("✅ Message sent!")
        
        # Wait for ACK response
        logger.info("⏳ Waiting for ACK response...")
        response = sock.recv(1024)
        
        if response:
            # Remove MLLP framing from response
            clean_response = response.strip(start_block + end_block + carriage_return)
            logger.info(f"📨 Received ACK: {clean_response.decode('utf-8')}")
            return clean_response.decode('utf-8')
        else:
            logger.warning("⚠️ No ACK received")
            return None
            
    except socket.timeout:
        logger.error("⏰ Timeout: Dr. Giggles must be busy with another patient!")
        return None
    except ConnectionRefusedError:
        logger.error("🚫 Connection refused: The HL7 listener must be taking a coffee break!")
        return None
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return None
    finally:
        if sock:
            sock.close()
            logger.info("🔌 Connection closed")

def print_message_header(message_type, description):
    """Print a fancy header for each message"""
    print(f"\n{'='*80}")
    print(f"🏥 {message_type.upper()} MESSAGE: {description}")
    print(f"{'='*80}")

def print_message_segments(message):
    """Print HL7 message with segment breaks for readability"""
    segments = message.strip().split('\n')
    for i, segment in enumerate(segments, 1):
        if segment.strip():
            segment_type = segment.split('|')[0]
            print(f"{i:2d}. {segment_type}: {segment}")

def main():
    """Main function to send both ADT and ORU messages"""
    print("🎭 Welcome to the Funny Farm Asylum HL7 Message Sender! 🎭")
    print("Preparing to admit Matt Knee-Slapper Jr. for his funny bone procedure...")
    
    # Build messages
    adt_message = build_adt_message()
    oru_message = build_oru_message()
    
    # Display ADT Message
    print_message_header("ADT", "Patient Admission for Funny Bone Surgery")
    print_message_segments(adt_message)
    
    # Display ORU Message  
    print_message_header("ORU", "Lab Results - Humor Level Critical!")
    print_message_segments(oru_message)
    
    # Send messages
    print(f"\n{'='*80}")
    print("🚀 SENDING MESSAGES TO HL7 LISTENER")
    print(f"{'='*80}")
    
    print("\n🏥 Sending ADT (Admission) Message...")
    adt_ack = send_hl7_message(adt_message)
    
    # Brief pause between messages
    time.sleep(1)
    
    print("\n🔬 Sending ORU (Lab Results) Message...")
    oru_ack = send_hl7_message(oru_message)
    
    # Summary
    print(f"\n{'='*80}")
    print("📋 TRANSMISSION SUMMARY")
    print(f"{'='*80}")
    print(f"ADT Message: {'✅ ACK Received' if adt_ack else '❌ No ACK'}")
    print(f"ORU Message: {'✅ ACK Received' if oru_ack else '❌ No ACK'}")
    print("\n🎉 Matt's funny bone procedure is now in the system!")
    print("Dr. Giggles will see him shortly for his comedy implant! 😄")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user")
        logger.info("User interrupted the program")
    except Exception as e:
        logger.error(f"💥 Unexpected error in main: {e}")
        print("\n😵 Something went wrong! Check the logs above.")
