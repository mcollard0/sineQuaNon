#!/bin/bash

# KVM Toggle Script
# Enables or disables KVM (Kernel Virtual Machine) support temporarily
# Useful for Android emulator performance tuning or switching virtualization modes

LOG_FILE="/tmp/kvm_toggle.log"
KVM_MODULE="kvm"
KVM_INTEL_MODULE="kvm_intel"
KVM_AMD_MODULE="kvm_amd"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo -e "$1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_message "${RED}Error: This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

# Function to check KVM status
check_kvm_status() {
    if lsmod | grep -q "^kvm"; then
        return 0  # KVM is loaded
    else
        return 1  # KVM is not loaded
    fi
}

# Function to detect CPU type and appropriate KVM module
detect_cpu_kvm_module() {
    if grep -q "Intel" /proc/cpuinfo; then
        echo "$KVM_INTEL_MODULE"
    elif grep -q "AMD" /proc/cpuinfo; then
        echo "$KVM_AMD_MODULE"
    else
        log_message "${YELLOW}Warning: Could not detect CPU type, defaulting to kvm_intel${NC}"
        echo "$KVM_INTEL_MODULE"
    fi
}

# Function to enable KVM
enable_kvm() {
    log_message "${BLUE}Enabling KVM...${NC}"
    
    # Load the base KVM module first
    if ! modprobe "$KVM_MODULE" 2>/dev/null; then
        log_message "${RED}Failed to load $KVM_MODULE module${NC}"
        return 1
    fi
    
    # Detect and load the appropriate CPU-specific module
    local cpu_module=$(detect_cpu_kvm_module)
    if ! modprobe "$cpu_module" 2>/dev/null; then
        log_message "${RED}Failed to load $cpu_module module${NC}"
        # Try to unload base module if CPU module failed
        rmmod "$KVM_MODULE" 2>/dev/null
        return 1
    fi
    
    # Set proper permissions for KVM device
    if [[ -e /dev/kvm ]]; then
        chmod 666 /dev/kvm
        log_message "${GREEN}KVM enabled successfully${NC}"
        log_message "${BLUE}KVM device: /dev/kvm (permissions: $(ls -l /dev/kvm | awk '{print $1}'))${NC}"
    else
        log_message "${RED}KVM device /dev/kvm not found after module load${NC}"
        return 1
    fi
    
    return 0
}

# Function to disable KVM
disable_kvm() {
    log_message "${BLUE}Disabling KVM...${NC}"
    
    # Unload CPU-specific modules first
    local cpu_module=$(detect_cpu_kvm_module)
    if lsmod | grep -q "^${cpu_module}"; then
        if ! rmmod "$cpu_module" 2>/dev/null; then
            log_message "${YELLOW}Warning: Could not unload $cpu_module (may be in use)${NC}"
        fi
    fi
    
    # Unload base KVM module
    if lsmod | grep -q "^${KVM_MODULE}"; then
        if ! rmmod "$KVM_MODULE" 2>/dev/null; then
            log_message "${YELLOW}Warning: Could not unload $KVM_MODULE (may be in use)${NC}"
            log_message "${YELLOW}Try stopping all VMs and emulators first${NC}"
            return 1
        fi
    fi
    
    log_message "${GREEN}KVM disabled successfully${NC}"
    return 0
}

# Function to show current status
show_status() {
    log_message "${BLUE}=== KVM Status ===${NC}"
    
    if check_kvm_status; then
        log_message "${GREEN}KVM: ENABLED${NC}"
        log_message "${BLUE}Loaded KVM modules:${NC}"
        lsmod | grep kvm | while read line; do
            log_message "  $line"
        done
        
        if [[ -e /dev/kvm ]]; then
            local kvm_perms=$(ls -l /dev/kvm | awk '{print $1" "$3" "$4}')
            log_message "${BLUE}/dev/kvm: EXISTS ($kvm_perms)${NC}"
        else
            log_message "${RED}/dev/kvm: NOT FOUND${NC}"
        fi
    else
        log_message "${RED}KVM: DISABLED${NC}"
    fi
    
    # Show CPU virtualization support
    if grep -q "vmx\|svm" /proc/cpuinfo; then
        local virt_flags=$(grep -o "vmx\|svm" /proc/cpuinfo | head -1)
        log_message "${GREEN}CPU Virtualization: SUPPORTED ($virt_flags)${NC}"
    else
        log_message "${RED}CPU Virtualization: NOT SUPPORTED${NC}"
    fi
}

# Function to show help
show_help() {
    cat << EOF
${BLUE}KVM Toggle Script${NC}
Usage: $0 [OPTION]

OPTIONS:
    enable      Enable KVM modules and set permissions
    disable     Disable KVM modules  
    status      Show current KVM status
    toggle      Toggle KVM state (enable if disabled, disable if enabled)
    help        Show this help message

EXAMPLES:
    sudo $0 enable      # Enable KVM
    sudo $0 disable     # Disable KVM
    sudo $0 status      # Check KVM status
    sudo $0 toggle      # Toggle current state

NOTE: This script requires root privileges (use sudo)

LOG FILE: $LOG_FILE
EOF
}

# Main script logic
main() {
    case "${1:-help}" in
        "enable")
            check_root
            if check_kvm_status; then
                log_message "${YELLOW}KVM is already enabled${NC}"
                show_status
            else
                enable_kvm
                show_status
            fi
            ;;
        "disable")
            check_root
            if ! check_kvm_status; then
                log_message "${YELLOW}KVM is already disabled${NC}"
                show_status
            else
                disable_kvm
                show_status
            fi
            ;;
        "toggle")
            check_root
            if check_kvm_status; then
                log_message "${BLUE}KVM is currently enabled, disabling...${NC}"
                disable_kvm
            else
                log_message "${BLUE}KVM is currently disabled, enabling...${NC}"
                enable_kvm
            fi
            show_status
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_message "${RED}Invalid option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Initialize log file
echo "=== KVM Toggle Script Started ===" > "$LOG_FILE"

# Run main function
main "$@"