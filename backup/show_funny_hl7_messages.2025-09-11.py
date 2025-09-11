#!/usr/bin/env python3
"""
Display Funny HL7 Messages
===========================
Shows the humorous ADT and ORU messages for Matt's funny bone procedure
without attempting to send them.

Author: AI Assistant
Date: 2025-09-04
"""

import datetime

def get_timestamp():
    """Generate HL7 timestamp format: YYYYMMDDHHMMSS"""
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def show_adt_message():
    """Display the humorous ADT message"""
    timestamp = get_timestamp()
    
    print("🏥 ADT^A01 MESSAGE (Patient Admission)")
    print("=" * 80)
    print("Patient: Matt Knee-Slapper Jr.")
    print("Doctor: Dr. Giggles Chuckle Laugh, MD")
    print("Facility: Funny Farm Asylum")
    print("Diagnosis: Acute Humerus Deficiency")
    print("Procedure: Funny Bone Reconstruction with Comedy Implant")
    print("=" * 80)
    
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
    
    print(message)
    return message

def show_oru_message():
    """Display the humorous ORU message"""
    timestamp = get_timestamp()
    observation_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    print("\n🔬 ORU^R01 MESSAGE (Lab Results)")
    print("=" * 80)
    print("Lab Results for: Matt Knee-Slapper Jr.")
    print("Humor Level: 2 LOL/dL (CRITICAL - Normal: 7-10)")
    print("Sarcasm Saturation: 98% (HIGH - Normal: 10-95%)")
    print("Funny Bone Density: 0.001 g/cm³ (CRITICALLY LOW)")
    print("=" * 80)
    
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
    
    print(message)
    return message

def main():
    """Main function to display both messages"""
    print("🎭 FUNNY FARM ASYLUM HL7 MESSAGES 🎭")
    print("For Matt Knee-Slapper Jr.'s Funny Bone Procedure")
    print("\n" + "🎪" * 40 + "\n")
    
    adt_msg = show_adt_message()
    oru_msg = show_oru_message()
    
    print("\n" + "🎪" * 40)
    print("\n✨ Both messages created successfully!")
    print("🎉 Matt is ready for his comedy implant!")

if __name__ == "__main__":
    main()
