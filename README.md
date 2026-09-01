# Intelligent Pick-and-Place Robot with Voice Control

> The current User Command Station work is isolated from the inherited robot
> implementation. See [Controlled typed UCS](docs/controlled-ucs.md) for the
> browser-based, confirmation-gated development slice.

**Author:** Timothy Tan (ICP Intern)  
**Email:** t.l.tan@student.curtin.edu.au  
**Organization:** Innovation Central Perth  
**Target Conference:** Indo-Pacific Robotics Conference (IPRAAC)

## 🤖 Project Overview

This repository contains a complete distributed AI-powered robotic control system that enables **voice-controlled and LLM-driven pick-and-place manipulation**. Users can issue natural language commands (e.g., "arrange the animals from largest to smallest") which are intelligently interpreted and executed by an Arduino Braccio robotic arm.

The system demonstrates cutting-edge integration of:
- **Generative AI (LLM)** for natural language understanding
- **Voice Recognition** for hands-free command input
- **MQTT** for distributed microservices communication
- **Arduino Braccio** for precision robotic manipulation
- **Real-time Status Tracking** and position feedback

---

## 🏗️ System Architecture

The project employs a distributed microservices architecture with three main components communicating via MQTT:

```
┌─────────────────────────────┐
│  User Command Station (UCS) │
│  • Voice Recognition        │
│  • LLM Processing           │
│  • Natural Language Support │
└──────────────┬──────────────┘
               │ MQTT
               ▼
┌─────────────────────────────┐
│   MQTT Message Broker       │
│  • stacker/command          │
│  • stacker/status           │
│  • stacker/positions        │
└──────────────┬──────────────┘
               │ MQTT
               ▼
┌─────────────────────────────┐
│  Stacker Controller (SC)    │
│  • Robot Hardware Interface │
│  • Movement Execution       │
│  • Position Tracking        │
└─────────────────────────────┘
```

---

## 📂 Repository Structure

### **1. Smart Stacker Frontend** (`smart_stacker_frontend/`)
The primary user-facing interface with voice recognition and LLM integration.

**Key Files:**
- `ucs_voice_safe.py` - Voice-controlled command interface (fallback mode)
- `ucs_voice_wifi.py` - Live voice recognition interface
- `llm_integration.py` - LLM processing engine (Gemma 3:4B via Ollama)
- `llm_system_prompt.txt` - Prompt engineering configuration
- `requirements.txt` - Python dependencies

**Capabilities:**
- Real-time microphone capture and speech-to-text
- Fallback to WAV file processing
- Natural language command interpretation
- JSON-based robot command generation
- Status feedback and metrics collection

---

### **2. MQTT8** (`MQTT8/`)
Backend control system handling robot communication and movement execution.

**Key Files:**
- `main.py` - MQTT broker and GUI orchestration
- `command_processor.py` - Command parsing and move sequencing
- `gui.py` - Visual interface for position tracking
- `serial_comm.py` - Arduino serial communication
- `mqtt_sub.py` / `mqtt_pub.py` - MQTT client operations
- `llm_pub.py` / `llm_sub.py` - LLM integration bridges

**Responsibilities:**
- MQTT topic subscription/publishing
- Robot movement command execution
- Position state management
- GUI updates and status reporting

---

### **3. Braccio Firmware** (`Braccio_11_wloop/`)
Arduino sketch for the Braccio robotic arm.

**Key File:**
- `Braccio_11_wloop.ino` - Complete arm control firmware

**Features:**
- Predefined position storage (A-F positions)
- Pick-and-place movement sequences
- Gripper control (open/close)
- Serial communication protocol
- Safe travel height management

**Command Format:**
```
A          → Move to position A (A-F available)
A,C        → Pick from A, place at C (safe pick-and-place)
80,120,125,50,10 → Direct joint angles
X          → Move to safe top position
Y          → Close gripper
Z          → Open gripper
H          → Wave gripper
L          → Loop animation sequence
```

---

### **4. Animal Game Logic** (`animal_all/`)
Various game logic implementations for interactive demonstrations.

**Includes:**
- Multiple game versions (v1-v5)
- Voice control integration
- Sound effects and feedback
- LLM-based game state management
- MQTT message handling

---

### **5. Documentation Files**
- `ICP Robotics.pdf` - Project technical specification
- `ICP_Report_Robot.docx.pdf` - Comprehensive project report

---

## ⚡ Quick Start Guide

### **Prerequisites**
- Python 3.10+
- Arduino IDE (for firmware uploads)
- MQTT Broker (Mosquitto or equivalent)
- Ollama (for local LLM deployment)
- Curtin University network access (for ICP team)

### **1. Install Dependencies**

```bash
cd smart_stacker_frontend
pip install -r requirements.txt
```

**Required Packages:**
- `paho-mqtt>=2.0.0` - MQTT client
- `requests>=2.31.0` - HTTP client for LLM API
- `SpeechRecognition>=3.10.0` - Voice input
- `PyAudio>=0.2.13` - Microphone support

### **2. Set Up LLM (Ollama)**

```bash
# Install Ollama from https://ollama.ai
# Download Gemma 3:4B model
ollama pull gemma3:4b

# Start Ollama service
ollama serve
# Runs on localhost:11434
```

### **3. Start MQTT Broker**

```bash
# On Linux/WSL2
sudo systemctl start mosquitto

# Or run in Docker
docker run -d --name mosquitto -p 1883:1883 eclipse-mosquitto
```

### **4. Upload Arduino Firmware**

1. Open Arduino IDE
2. Load `Braccio_11_wloop/Braccio_11_wloop.ino`
3. Select Board: "Arduino Uno"
4. Select Port: (appropriate COM/ttyUSB)
5. Click Upload

### **5. Run the System**

**Terminal 1 - Backend Controller:**
```bash
cd MQTT8
python main.py
```

**Terminal 2 - Voice Interface:**
```bash
cd smart_stacker_frontend
python ucs_voice_safe.py  # (fallback mode)
# OR
python ucs_voice_wifi.py   # (live microphone)
```

---

## 🎮 Game Mechanics

### **Available Animals (Game Objects)**
| Animal | Code | Size | Speed | Weight |
|--------|------|------|-------|--------|
| Elephant | E | Large | Slow | Heavy |
| Lion | L | Medium | Fast | Medium |
| Baby Bear/Frog | F | Small | Slow | Light |

### **Available Positions**
```
     L1  ROBOT  R1
     L2    C    R2

L1 = Left Back
L2 = Left Front
C  = Center Front
R1 = Right Back
R2 = Right Front
```

### **Command Examples**

**User Input:** "Arrange animals from big to small"  
**Generated Command:** `{"E": "L1", "L": "L2", "F": "C"}`

**User Input:** "Put elephant in back right"  
**Generated Command:** `{"E": "R1", "L": "L2", "F": "C"}`

**User Input:** "Move all animals to the front"  
**Generated Command:** `{"E": "L2", "L": "C", "F": "R2"}`

---

## 🧠 LLM Integration

### **Model Configuration**
- **Model:** Gemma 3:4B (via Ollama)
- **Base URL:** `http://localhost:11434`
- **Temperature:** 0.1 (low randomness for consistent commands)
- **Max Tokens:** 100 (efficient responses)

### **Prompt Engineering**
The system uses prompt engineering to ensure:
1. Only valid animals (E, L, F) are used
2. Only valid positions (L1, L2, C, R1, R2) are commanded
3. No two animals occupy the same position
4. Spatial relationships are correctly interpreted
5. JSON output format is strictly enforced

### **Command Validation**
All LLM outputs are validated against:
- Valid animal codes (E, L, F)
- Valid position codes (L1, L2, C, R1, R2)
- Non-conflicting position assignments
- Schema compliance

### **Fallback Mechanism**
If LLM processing fails:
1. System logs the error
2. Falls back to rule-based command interpretation
3. Maintains current robot state as safe default
4. Reports failure to user with guidance

---

## 🔌 MQTT Topic Structure

| Topic | Direction | Format | Purpose |
|-------|-----------|--------|---------|
| `stacker/command` | UCS → SC | JSON | Robot movement commands |
| `stacker/status` | SC → UCS | String | Status ("BUSY"/"DONE") |
| `stacker/positions` | SC → UCS | JSON | Current animal positions |

### **Message Examples**

**Command:**
```json
{"E": "L1", "L": "L2", "F": "C"}
```

**Status:**
```
BUSY
DONE - Final Positions: {"E": "L1", "L": "L2", "F": "C"}
```

**Positions:**
```json
{"E": "L1", "L": "L2", "F": "C"}
```

---

## 📊 Performance Metrics

The system collects academic metrics for research evaluation:

- **Total Commands Processed:** Count of all user commands
- **Success Rate:** Percentage of successfully executed commands
- **Average Processing Time:** Mean LLM response latency
- **Average Confidence Score:** Mean confidence of generated commands
- **Error Types:** Classification of failure modes

**Metrics are logged to:** `llm_robot_commands.log`

---

## 🔧 Technical Stack

| Component | Technology |
|-----------|-----------|
| Programming Language | Python 3.12 |
| Voice Recognition | SpeechRecognition + Google API |
| LLM Engine | Ollama + Gemma 3:4B |
| Message Broker | MQTT (Mosquitto) |
| Robot Control | Arduino Braccio++ |
| Serial Communication | PySerial |
| Hardware Platform | Arduino Uno / Braccio Arm |
| Development Environment | Ubuntu 22/WSL2 |
| Production Platform | Raspberry Pi 5 (Debian Bookworm) |

---

## 🚀 Advanced Features

### **Cross-Platform Compatibility**
- Runs on Windows (WSL2), Linux, macOS
- Automatic microphone detection
- Fallback to WAV file input when live audio unavailable
- Docker support for MQTT broker

### **Academic Features**
- Comprehensive logging and metrics collection
- Confidence scoring for generated commands
- Error tracking and analysis
- Performance benchmarking capabilities

### **Extensibility**
- Modular LLM integration (easy to swap models)
- Configurable prompt system (external file-based)
- Hardware abstraction layer for robot control
- Scalable MQTT architecture for multi-robot systems

---

## 📋 Configuration

### **Environment Variables** (if using)
```bash
MQTT_BROKER=localhost
MQTT_PORT=1883
LLM_MODEL=gemma3:4b
LLM_BASE_URL=http://localhost:11434
```

### **System Prompt** (`llm_system_prompt.txt`)
Contains the prompt engineering configuration. Modify this file to:
- Change command interpretation rules
- Add new valid positions or animals
- Adjust LLM behavior without code changes

---

## 🐛 Troubleshooting

### **LLM Connection Issues**
```
Error: Connection Error to localhost:11434
```
**Solution:** Ensure Ollama is running (`ollama serve`)

### **MQTT Connection Failed**
```
Error: Connection refused to localhost:1883
```
**Solution:** Start MQTT broker (`mosquitto` or Docker)

### **Arduino Not Found**
```
Error: Serial port not detected
```
**Solution:** 
- Check USB cable connection
- Install CH340 drivers (if using clone boards)
- Verify correct COM port in Arduino IDE

### **Microphone Not Working**
```
Error: No microphone detected
```
**Solution:** Use fallback mode (`ucs_voice_safe.py` with WAV files)

### **LLM Generating Invalid Commands**
```
Invalid JSON or invalid position codes
```
**Solution:** 
- Check `llm_system_prompt.txt` syntax
- Verify Ollama model is fully downloaded
- Lower temperature value in `llm_integration.py`

---

## 📚 Documentation Files

- **Technical Specification:** `ICP Robotics.pdf`
- **Full Project Report:** `ICP_Report_Robot.docx.pdf`
- **This README:** Complete system overview and quick start

---

## 🎯 Research & Educational Value

This system demonstrates:

1. **Human-Robot Interaction (HRI)**
   - Natural language interfaces for robotic control
   - Voice-driven automation in industrial applications

2. **Distributed Systems**
   - Microservices architecture for robotics
   - MQTT-based inter-process communication
   - Scalable system design

3. **Generative AI Integration**
   - Local LLM deployment for low-latency robotics
   - Prompt engineering for safety-critical systems
   - Context-aware command interpretation

4. **Cross-Platform Development**
   - WSL2 development workflow
   - Hardware abstraction for multiple platforms
   - Seamless transition from development to production

---

## 🚀 Future Enhancements

### **Planned Improvements**
- Computer vision for position verification
- Multi-robot coordination capabilities
- Mobile app interface development
- Cloud-based LLM integration options
- Advanced gesture recognition

### **Research Extensions**
- Reinforcement learning for optimized movement paths
- Predictive command completion
- Multi-modal input (voice + gesture)
- Safety verification using formal methods
- Performance benchmarking against competing systems

---

## 📜 License & Attribution

**Project:** Intelligent Pick-and-Place Robot with Voice Control  
**Author:** Timothy Tan (ICP Intern)  
**Contact:** t.l.tan@student.curtin.edu.au  
**Organization:** Innovation Central Perth  
**Created:** 2025  
**Purpose:** Educational demonstration for IPRAAC Conference

---

## 🤝 Contributing

For contributions or questions about this project:
- Contact: Timothy Tan at t.l.tan@student.curtin.edu.au
- Organization: Innovation Central Perth
- Repository: https://github.com/InnovationCentralPerth/intelligent-pick-place-robot

---

**System designed for educational and research purposes**  
**Conference: Indo-Pacific Robotics Conference (IPRAAC)**  
**Curtin University & Innovation Central Perth**
