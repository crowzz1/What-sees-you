/**
 * ESP32 控制 SERVO42C - CR_UART 模式
 * 
 * 基于 GitHub 库改写：
 * https://github.com/G-EDM/SERVO42C-ESP32WROOM32-UART-Library
 * 
 * 重要：电机必须设置为 CR_UART 模式！
 * 
 * 接线：
 * ESP32 GPIO16 (RX) → SERVO42C TX
 * ESP32 GPIO17 (TX) → SERVO42C RX
 * ESP32 GND         → SERVO42C GND
 */

#define SERVO_BAUDRATE 38400
#define DEBUG_BAUDRATE 115200

// 命令码定义
#define CMD_GET_ENCODER_VALUES             0x30
#define CMD_GET_NUMPULSES_RECEIVED         0x33
#define CMD_GET_SHAFT_ANGLE_ERROR          0x39
#define CMD_GET_ENABLE_PIN_STATE           0x3A
#define CMD_GET_SHAFT_LOCK_STATE           0x3E
#define CMD_SET_ENABLE_STATE               0xF3
#define CMD_SET_RUN_CONTINUOUS             0xF6
#define CMD_SET_STOP_MOTOR                 0xF7
#define CMD_SET_RUN_BY_STEPNUM             0xFD

HardwareSerial ServoSerial(2);

// 全局变量
uint8_t slave_address = 0;  // 会在 setup 中初始化为 0xE0
uint8_t txBuffer[20];
uint8_t rxBuffer[20];

void setup() {
    Serial.begin(DEBUG_BAUDRATE);
    delay(1000);
    
    Serial.println("\n\n");
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  ESP32 控制 SERVO42C - CR_UART 模式       ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("重要：电机必须设置为 CR_UART 模式！");
    Serial.println();
    
    // 初始化串口
    Serial.println("初始化串口...");
    ServoSerial.begin(SERVO_BAUDRATE, SERIAL_8N1, 16, 17);
    delay(500);
    Serial.println("✓ 串口初始化完成");
    Serial.println();
    
    // 初始化地址（关键！）
    Serial.println("设置电机地址...");
    initSlaveAddress(0);  // 地址参数 0 = 实际地址 0xE0
    Serial.print("  从机地址: 0x");
    Serial.println(slave_address, HEX);
    Serial.println();
    
    // 等待电机准备
    delay(2000);
    
    // 通信测试
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  通信测试                                 ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    
    testCommunication();
    
    Serial.println();
    printHelp();
}

void loop() {
    // 处理串口命令
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        cmd.toLowerCase();
        
        if (cmd.length() > 0) {
            handleCommand(cmd);
        }
    }
    
    delay(10);
}

/**
 * 初始化从机地址
 * address_num: 0-9，实际地址 = 0xE0 + address_num
 */
void initSlaveAddress(uint8_t address_num) {
    if (address_num > 9) address_num = 9;
    slave_address = 0xE0 + address_num;
}

/**
 * 计算校验和
 */
uint8_t calculateChecksum(uint8_t* data, int len) {
    uint16_t sum = 0;
    for (int i = 0; i < len; i++) {
        sum += data[i];
    }
    return (uint8_t)(sum & 0xFF);
}

/**
 * 发送并接收数据
 */
bool sendReceive(uint8_t* tx, int txLen, uint8_t* rx, int rxLen) {
    // 打印发送数据
    Serial.print("  发送: ");
    printHex(tx, txLen);
    
    // 清空接收缓冲
    while (ServoSerial.available()) {
        ServoSerial.read();
    }
    
    // 发送
    ServoSerial.write(tx, txLen);
    ServoSerial.flush();
    
    // 接收
    unsigned long startTime = millis();
    int rxIndex = 0;
    
    while (millis() - startTime < 3000) {
        if (ServoSerial.available()) {
            uint8_t byte = ServoSerial.read();
            
            // 第一个字节必须是从机地址
            if (rxIndex == 0 && byte != slave_address) {
                continue;
            }
            
            rx[rxIndex++] = byte;
            
            // 收够了
            if (rxIndex >= rxLen) {
                // 验证校验和
                uint8_t calcChecksum = calculateChecksum(rx, rxLen - 1);
                uint8_t recvChecksum = rx[rxLen - 1];
                
                Serial.print("  收到: ");
                printHex(rx, rxLen);
                
                if (calcChecksum == recvChecksum) {
                    Serial.println("  ✓ 校验成功");
                    return true;
                } else {
                    Serial.println("  ✗ 校验失败");
                    return false;
                }
            }
        }
        delay(1);
    }
    
    if (rxIndex > 0) {
        Serial.print("  收到（不完整）: ");
        printHex(rx, rxIndex);
    } else {
        Serial.println("  ✗ 超时，无响应");
    }
    
    return false;
}

/**
 * 通信测试
 */
void testCommunication() {
    // 测试 1: 读取使能状态
    Serial.println("测试 1: 读取使能状态");
    readEnableStatus();
    delay(500);
    Serial.println();
    
    // 测试 2: 读取编码器值
    Serial.println("测试 2: 读取编码器值");
    readEncoderValue();
    delay(500);
    Serial.println();
    
    // 测试 3: 读取累计脉冲
    Serial.println("测试 3: 读取累计脉冲");
    readPulsesReceived();
    delay(500);
    Serial.println();
}

/**
 * 读取使能状态
 */
void readEnableStatus() {
    txBuffer[0] = slave_address;
    txBuffer[1] = CMD_GET_ENABLE_PIN_STATE;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 3)) {
        uint8_t status = rxBuffer[1];
        if (status == 1) {
            Serial.println("  → 状态: 已使能");
        } else if (status == 2) {
            Serial.println("  → 状态: 未使能");
        } else {
            Serial.println("  → 状态: 错误");
        }
    }
}

/**
 * 读取编码器值
 */
void readEncoderValue() {
    txBuffer[0] = slave_address;
    txBuffer[1] = CMD_GET_ENCODER_VALUES;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 8)) {
        // 解析：carrier (int32) + value (uint16)
        int32_t carrier = ((int32_t)rxBuffer[1] << 24) | ((int32_t)rxBuffer[2] << 16) |
                          ((int32_t)rxBuffer[3] << 8) | rxBuffer[4];
        uint16_t value = ((uint16_t)rxBuffer[5] << 8) | rxBuffer[6];
        
        int64_t totalValue = ((int64_t)carrier * 65536LL) + (int64_t)value;
        float angle = (value * 360.0) / 65536.0;
        
        Serial.print("  → 编码器值: ");
        Serial.print(totalValue);
        Serial.print(" (当前角度: ");
        Serial.print(angle, 2);
        Serial.println("°)");
    }
}

/**
 * 读取累计脉冲
 */
void readPulsesReceived() {
    txBuffer[0] = slave_address;
    txBuffer[1] = CMD_GET_NUMPULSES_RECEIVED;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 6)) {
        int32_t pulses = ((int32_t)rxBuffer[1] << 24) | ((int32_t)rxBuffer[2] << 16) |
                         ((int32_t)rxBuffer[3] << 8) | rxBuffer[4];
        Serial.print("  → 累计脉冲: ");
        Serial.println(pulses);
    }
}

/**
 * 使能电机
 */
void enableMotor() {
    Serial.println("使能电机...");
    
    txBuffer[0] = slave_address;
    txBuffer[1] = CMD_SET_ENABLE_STATE;
    txBuffer[2] = 0x01;  // 1 = enable
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    if (sendReceive(txBuffer, 4, rxBuffer, 3)) {
        if (rxBuffer[1] == 1) {
            Serial.println("  ✓ 使能成功");
        } else {
            Serial.println("  ✗ 使能失败");
        }
    }
}

/**
 * 失能电机
 */
void disableMotor() {
    Serial.println("失能电机...");
    
    txBuffer[0] = slave_address;
    txBuffer[1] = CMD_SET_ENABLE_STATE;
    txBuffer[2] = 0x00;  // 0 = disable
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    if (sendReceive(txBuffer, 4, rxBuffer, 3)) {
        if (rxBuffer[1] == 1) {
            Serial.println("  ✓ 失能成功");
        } else {
            Serial.println("  ✗ 失能失败");
        }
    }
}

/**
 * 停止电机
 */
void stopMotor() {
    Serial.println("停止电机...");
    
    txBuffer[0] = slave_address;
    txBuffer[1] = CMD_SET_STOP_MOTOR;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 3)) {
        if (rxBuffer[1] == 1) {
            Serial.println("  ✓ 停止成功");
        } else {
            Serial.println("  ✗ 停止失败");
        }
    }
}

/**
 * 连续运动
 */
void runContinuous(uint8_t dir, uint8_t speed) {
    Serial.print("连续运动: 方向=");
    Serial.print(dir == 0 ? "正向" : "反向");
    Serial.print(", 速度=");
    Serial.println(speed);
    
    if (speed > 127) speed = 127;
    uint8_t value = (dir == 1 ? 0x80 : 0x00) | speed;
    
    txBuffer[0] = slave_address;
    txBuffer[1] = CMD_SET_RUN_CONTINUOUS;
    txBuffer[2] = value;
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    if (sendReceive(txBuffer, 4, rxBuffer, 3)) {
        if (rxBuffer[1] == 1) {
            Serial.println("  ✓ 运动开始");
        } else {
            Serial.println("  ✗ 运动失败");
        }
    }
}

/**
 * 处理命令
 */
void handleCommand(String cmd) {
    Serial.print("\n→ 命令: ");
    Serial.println(cmd);
    Serial.println();
    
    if (cmd == "enable" || cmd == "en") {
        enableMotor();
    }
    else if (cmd == "disable" || cmd == "dis") {
        disableMotor();
    }
    else if (cmd == "stop") {
        stopMotor();
    }
    else if (cmd == "forward" || cmd == "fwd") {
        runContinuous(0, 50);  // 正向，速度 50
    }
    else if (cmd == "reverse" || cmd == "rev") {
        runContinuous(1, 50);  // 反向，速度 50
    }
    else if (cmd == "fast") {
        runContinuous(0, 100);  // 快速正向
    }
    else if (cmd == "encoder" || cmd == "enc") {
        readEncoderValue();
    }
    else if (cmd == "pulses" || cmd == "pulse") {
        readPulsesReceived();
    }
    else if (cmd == "status") {
        readEnableStatus();
    }
    else if (cmd == "test") {
        testCommunication();
    }
    else if (cmd == "help" || cmd == "h") {
        printHelp();
    }
    else {
        Serial.println("✗ 未知命令，输入 'help' 查看帮助");
    }
    
    Serial.println();
}

/**
 * 打印十六进制
 */
void printHex(uint8_t* data, int len) {
    for (int i = 0; i < len; i++) {
        if (data[i] < 0x10) Serial.print("0");
        Serial.print(data[i], HEX);
        Serial.print(" ");
    }
    Serial.println();
}

/**
 * 打印帮助
 */
void printHelp() {
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  可用命令                                 ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("【控制命令】");
    Serial.println("  enable     - 使能电机");
    Serial.println("  disable    - 失能电机");
    Serial.println("  forward    - 正向运动（速度 50）");
    Serial.println("  reverse    - 反向运动（速度 50）");
    Serial.println("  fast       - 快速正向（速度 100）");
    Serial.println("  stop       - 停止电机");
    Serial.println();
    Serial.println("【查询命令】");
    Serial.println("  status     - 查询使能状态");
    Serial.println("  encoder    - 查询编码器值");
    Serial.println("  pulses     - 查询累计脉冲");
    Serial.println();
    Serial.println("【其他】");
    Serial.println("  test       - 重新运行通信测试");
    Serial.println("  help       - 显示此帮助");
    Serial.println();
    Serial.println("注意：电机必须配置为 CR_UART 模式！");
    Serial.println();
}

