# Sinequanon Repository

## Funny HL7 Messages for Matt

This repository contains humorous HL7 2.2 messages and Python scripts for Matt's admission to the Funny Farm Asylum for his funny bone procedure.

### Files

- **`funny_hl7_sender.py`** - Main script that builds and sends both ADT and ORU messages via TCP with MLLP framing
- **`hl7_test_listener.py`** - Test listener that accepts HL7 messages and responds with ACK messages  
- **`show_funny_hl7_messages.py`** - Displays the humorous messages without sending them

### The Case

**Patient**: Matt Knee-Slapper Jr.  
**Doctor**: Dr. Giggles Chuckle Laugh, MD  
**Facility**: Funny Farm Asylum  
**Diagnosis**: Acute Humerus Deficiency  
**Procedure**: Funny Bone Reconstruction with Comedy Implant  

### Usage

```bash
# View messages only
python3 show_funny_hl7_messages.py

# Start test listener (Terminal 1)
python3 hl7_test_listener.py

# Send messages (Terminal 2) 
python3 funny_hl7_sender.py
```

### Lab Results Highlights

- **Humor Level**: 2 LOL/dL (CRITICAL - Normal: 7-10)
- **Sarcasm Saturation**: 98% (HIGH) 
- **Pun Tolerance**: 0.1 GROAN/JOKE (CRITICALLY LOW)
- **Funny Bone Density**: 0.001 g/cm³ (DANGEROUSLY LOW)

*Created for Matt with love and laughter* 🎭
