/**
 * ESP32 控制 4 个 SERVO42C - 机械臂控制
 * 
 * 4个电机地址：
 * 0xE0 - 电机1 (基座)
 * 0xE1 - 电机2 (大臂)
 * 0xE2 - 电机3 (小臂)
 * 0xE3 - 电机4 (手腕)
 * 
 * 接线：
 * ESP32 GPIO16 (RX) → 所有 SERVO42C 的 TX (并联)
 * ESP32 GPIO17 (TX) → 所有 SERVO42C 的 RX (并联)
 * ESP32 GND         → 所有 SERVO42C 的 GND (共地)
 */

#define SERVO_BAUDRATE 38400
#define DEBUG_BAUDRATE 115200

// 电机地址
#define MOTOR1_ADDR 0xE0  // 基座
#define MOTOR2_ADDR 0xE1  // 大臂
#define MOTOR3_ADDR 0xE2  // 小臂
#define MOTOR4_ADDR 0xE3  // 手腕

// 减速比配置 (电机轴:输出轴)
// 如果没有减速器，设为 1.0
// 如果是 1:8 减速器，设为 8.0
const float GEAR_RATIO[4] = {
    8.0,   // 电机1的减速比 (基座) - 1:8
    8.0,   // 电机2的减速比 (大臂) - 1:8
    8.0,   // 电机3的减速比 (小臂) - 1:8
    8.0    // 电机4的减速比 (手腕) - 1:8
};

// 命令码 - 严格按照文档定义
#define CMD_GET_ENCODER_VALUES       0x30  // 读取编码器值
#define CMD_GET_PULSE_COUNT          0x33  // 读取累计脉冲数
#define CMD_GET_REALTIME_POSITION    0x36  // 读取实时位置
#define CMD_GET_ENABLE_PIN_STATE     0x3A  // 读取使能引脚状态
#define CMD_SET_WORK_MODE            0x82  // 设置工作模式
#define CMD_SET_ZERO_POINT           0x91  // 设置零点
#define CMD_GOTO_ZERO                0x94  // 回零
#define CMD_SET_ACCELERATION         0xA4  // 设置加速度
#define CMD_SET_ENABLE_STATE         0xF3  // 使能/失能
#define CMD_SET_RUN_CONTINUOUS       0xF6  // 连续运动
#define CMD_SET_STOP_MOTOR           0xF7  // 停止
#define CMD_SET_RUN_BY_STEPNUM       0xFD  // 按脉冲数运动

// 工作模式定义
#define MODE_CR_OPEN   0x00  // 开环模式
#define MODE_CR_vFOC   0x01  // 闭环模式 (STD/DIR接口)
#define MODE_CR_UART   0x02  // 闭环模式 (UART接口) - 0xFD命令需要此模式

HardwareSerial ServoSerial(2);

// 缓冲区
uint8_t txBuffer[20];
uint8_t rxBuffer[20];

// 电机状态
bool motor_enabled[4] = {false, false, false, false};

// 零点位置（输出轴角度，单位：度）
float zero_angles[4] = {0.0, 0.0, 0.0, 0.0};

// 当前目标角度
float target_angles[4] = {0.0, 0.0, 0.0, 0.0};

// 函数声明
uint8_t calculateChecksum(uint8_t* data, int len);
bool sendReceive(uint8_t* tx, int txLen, uint8_t* rx, int rxLen, bool verbose = true);
bool testMotor(uint8_t addr);
void testAllMotors();
void printHex(uint8_t* data, int len);
float getCurrentAngle(uint8_t motorNum);
void setZeroPosition(uint8_t motorNum);
void moveToAngle(uint8_t motorNum, float targetAngle, int speed);

void setup() {
    Serial.begin(DEBUG_BAUDRATE);
    delay(1000);
    
    Serial.println("\n\n");
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  4轴机械臂控制系统                        ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("电机地址：");
    Serial.println("  电机1 (基座): 0xE0");
    Serial.println("  电机2 (大臂): 0xE1");
    Serial.println("  电机3 (小臂): 0xE2");
    Serial.println("  电机4 (手腕): 0xE3");
    Serial.println();
    
    // 初始化串口
    Serial.println("初始化串口...");
    // RX=16, TX=17
    ServoSerial.begin(SERVO_BAUDRATE, SERIAL_8N1, 16, 17);
    delay(500);
    Serial.println("✓ 串口初始化完成 (RX=GPIO16, TX=GPIO17)");
    Serial.println();
    
    // 等待电机准备
    delay(2000);
    
    // 系统就绪
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  系统就绪                                 ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("✓ 4个电机地址已配置:");
    Serial.println("  - 电机1: 0xE0");
    Serial.println("  - 电机2: 0xE1");
    Serial.println("  - 电机3: 0xE2");
    Serial.println("  - 电机4: 0xE3");
    Serial.println();
    
    // 显示减速比配置
    Serial.println("减速比配置:");
    for (int i = 0; i < 4; i++) {
        Serial.print("  - 电机");
        Serial.print(i + 1);
        Serial.print(": ");
        if (GEAR_RATIO[i] > 1.0) {
            Serial.print("1:");
            Serial.print((int)GEAR_RATIO[i]);
            Serial.print(" 减速器");
            Serial.print(" (输出扭矩×");
            Serial.print((int)GEAR_RATIO[i]);
            Serial.print(", 输出速度÷");
            Serial.print((int)GEAR_RATIO[i]);
            Serial.println(")");
        } else {
            Serial.println("直驱（无减速器）");
        }
    }
    Serial.println();
    Serial.println("提示: 如需测试通信，输入 'test'");
    Serial.println();
    printHelp();
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        cmd.toLowerCase();  // 恢复toLowerCase，改用小写命令名
        
        if (cmd.length() > 0) {
            handleCommand(cmd);
        }
    }
    
    delay(10);
}

/**
 * 测试所有电机
 */
void testAllMotors() {
    Serial.println("测试所有电机通信...");
    Serial.println();
    
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    for (int i = 0; i < 4; i++) {
        Serial.print("电机");
        Serial.print(i + 1);
        Serial.print(" (0x");
        Serial.print(addresses[i], HEX);
        Serial.println("):");
        
        txBuffer[0] = addresses[i];
        txBuffer[1] = CMD_GET_ENABLE_PIN_STATE;
        txBuffer[2] = calculateChecksum(txBuffer, 2);
        
        if (sendReceive(txBuffer, 3, rxBuffer, 3, true)) {
            Serial.println("  ✓ 通信正常");
            motor_enabled[i] = true;
        } else {
            Serial.println("  ✗ 无响应");
            motor_enabled[i] = false;
        }
        
        Serial.println();
        delay(300);
    }
    
    Serial.println("─────────────────────────");
    int successCount = 0;
    for (int i = 0; i < 4; i++) {
        if (motor_enabled[i]) successCount++;
    }
    Serial.print("测试完成: ");
    Serial.print(successCount);
    Serial.print("/4 电机通信正常");
    Serial.println();
}

/**
 * 测试单个电机
 */
bool testMotor(uint8_t addr) {
    txBuffer[0] = addr;
    txBuffer[1] = CMD_GET_ENABLE_PIN_STATE;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    return sendReceive(txBuffer, 3, rxBuffer, 3, false);
}

/**
 * 扫描所有可能的地址 (包括常用地址)
 * 找出实际连接的电机
 */
void scanAllAddresses() {
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  扫描电机地址                             ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    
    int foundCount = 0;
    uint8_t foundAddresses[10];  // 存储找到的地址
    
    // 扫描常用地址范围
    Serial.println("扫描地址 0xE0-0xE7:");
    for (uint8_t addr = 0xE0; addr <= 0xE7; addr++) {
        Serial.print("测试地址 0x");
        Serial.print(addr, HEX);
        Serial.print(": ");
        
        txBuffer[0] = addr;
        txBuffer[1] = CMD_GET_ENABLE_PIN_STATE;
        txBuffer[2] = calculateChecksum(txBuffer, 2);
        
        // 清空接收缓冲（更彻底）
        delay(10);  // 等待之前的数据传输完成
        while (ServoSerial.available()) {
            ServoSerial.read();
        }
        delay(10);  // 再次等待
        
        // 发送
        ServoSerial.write(txBuffer, 3);
        ServoSerial.flush();
        
        // 接收（增加超时时间）
        unsigned long startTime = millis();
        int rxIndex = 0;
        bool isEcho = false;
        
        while (millis() - startTime < 500) {  // 增加到500ms
            if (ServoSerial.available()) {
                uint8_t byte = ServoSerial.read();
                
                if (rxIndex == 0 && byte != addr) {
                    continue;
                }
                
                rxBuffer[rxIndex++] = byte;
                
                if (rxIndex >= 3) {
                    // 检查是否是回显
                    if (rxBuffer[1] == CMD_GET_ENABLE_PIN_STATE) {
                        isEcho = true;
                        Serial.println("回显（无响应）");
                    } else {
                        // 验证校验和
                        uint8_t calcChecksum = calculateChecksum(rxBuffer, 2);
                        if (calcChecksum == rxBuffer[2]) {
                            Serial.print("✓ 找到电机！响应数据: ");
                            printHex(rxBuffer, 3);
                            foundAddresses[foundCount] = addr;
                            foundCount++;
                        } else {
                            Serial.println("✗ 校验失败");
                        }
                    }
                    break;
                }
            }
            delay(1);
        }
        
        if (rxIndex == 0) {
            Serial.println("无响应");
        }
        
        delay(200);  // 增加到200ms，让电机有时间恢复
    }
    
    Serial.println();
    Serial.println("提示：等待电机准备下一轮扫描...");
    delay(1000);  // 在扫描其他地址前等待1秒
    
    // 扫描其他可能的地址
    Serial.println();
    Serial.println("扫描其他常用地址:");
    
    uint8_t otherAddresses[] = {0x00, 0x01, 0x10, 0x20, 0x30, 0x40, 0x50, 0xF0, 0xFE, 0xFF};
    
    for (int i = 0; i < 10; i++) {
        uint8_t addr = otherAddresses[i];
        Serial.print("测试地址 0x");
        if (addr < 0x10) Serial.print("0");
        Serial.print(addr, HEX);
        Serial.print(": ");
        
        txBuffer[0] = addr;
        txBuffer[1] = CMD_GET_ENABLE_PIN_STATE;
        txBuffer[2] = calculateChecksum(txBuffer, 2);
        
        delay(10);
        while (ServoSerial.available()) {
            ServoSerial.read();
        }
        delay(10);
        
        ServoSerial.write(txBuffer, 3);
        ServoSerial.flush();
        
        unsigned long startTime = millis();
        int rxIndex = 0;
        
        while (millis() - startTime < 500) {  // 增加到500ms
            if (ServoSerial.available()) {
                uint8_t byte = ServoSerial.read();
                
                if (rxIndex == 0 && byte != addr) {
                    continue;
                }
                
                rxBuffer[rxIndex++] = byte;
                
                if (rxIndex >= 3) {
                    if (rxBuffer[1] == CMD_GET_ENABLE_PIN_STATE) {
                        Serial.println("回显（无响应）");
                    } else {
                        uint8_t calcChecksum = calculateChecksum(rxBuffer, 2);
                        if (calcChecksum == rxBuffer[2]) {
                            Serial.print("✓ 找到电机！响应数据: ");
                            printHex(rxBuffer, 3);
                            foundAddresses[foundCount] = addr;
                            foundCount++;
                        } else {
                            Serial.println("✗ 校验失败");
                        }
                    }
                    break;
                }
            }
            delay(1);
        }
        
        if (rxIndex == 0) {
            Serial.println("无响应");
        }
        
        delay(200);  // 增加到200ms
    }
    
    Serial.println();
    Serial.println("═════════════════════════════════════════");
    Serial.print("扫描完成: 找到 ");
    Serial.print(foundCount);
    Serial.println(" 个电机");
    
    if (foundCount > 0) {
        Serial.println();
        Serial.println("找到的电机地址:");
        for (int i = 0; i < foundCount; i++) {
            Serial.print("  电机");
            Serial.print(i + 1);
            Serial.print(": 0x");
            if (foundAddresses[i] < 0x10) Serial.print("0");
            Serial.print(foundAddresses[i], HEX);
            
            // 标注期望的地址
            uint8_t expectedAddresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
            bool isExpected = false;
            int motorNum = -1;
            for (int j = 0; j < 4; j++) {
                if (foundAddresses[i] == expectedAddresses[j]) {
                    isExpected = true;
                    motorNum = j + 1;
                    break;
                }
            }
            
            if (isExpected) {
                Serial.print(" ✓ (配置为电机");
                Serial.print(motorNum);
                Serial.println(")");
            } else {
                Serial.println(" ⚠ (未配置)");
            }
        }
    }
    
    Serial.println("═════════════════════════════════════════");
    Serial.println();
}

/**
 * 慢速稳定扫描 - 每次扫描3遍取一致结果
 */
void scanSlowAndSteady() {
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  慢速稳定扫描 (每个地址测试3次)          ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("⏱ 这需要大约30秒...");
    Serial.println();
    
    uint8_t testAddresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    bool motorFound[4] = {false, false, false, false};
    int testPassed[4] = {0, 0, 0, 0};
    
    for (int motorNum = 0; motorNum < 4; motorNum++) {
        uint8_t addr = testAddresses[motorNum];
        
        Serial.print("测试电机");
        Serial.print(motorNum + 1);
        Serial.print(" (0x");
        Serial.print(addr, HEX);
        Serial.println("):");
        
        // 测试3次
        for (int attempt = 1; attempt <= 3; attempt++) {
            Serial.print("  尝试 ");
            Serial.print(attempt);
            Serial.print("/3: ");
            
            // 彻底清空缓冲
            delay(100);
            while (ServoSerial.available()) {
                ServoSerial.read();
            }
            delay(100);
            
            // 发送命令
            txBuffer[0] = addr;
            txBuffer[1] = CMD_GET_ENABLE_PIN_STATE;
            txBuffer[2] = calculateChecksum(txBuffer, 2);
            
            ServoSerial.write(txBuffer, 3);
            ServoSerial.flush();
            
            // 等待响应
            unsigned long startTime = millis();
            int rxIndex = 0;
            bool success = false;
            
            while (millis() - startTime < 1000) {  // 1秒超时
                if (ServoSerial.available()) {
                    uint8_t byte = ServoSerial.read();
                    
                    if (rxIndex == 0 && byte != addr) {
                        continue;
                    }
                    
                    rxBuffer[rxIndex++] = byte;
                    
                    if (rxIndex >= 3) {
                        // 检查是否是回显
                        if (rxBuffer[1] == CMD_GET_ENABLE_PIN_STATE) {
                            Serial.println("回显（无响应）");
                        } else {
                            // 验证校验和
                            uint8_t calcChecksum = calculateChecksum(rxBuffer, 2);
                            if (calcChecksum == rxBuffer[2]) {
                                Serial.println("✓ 响应正常");
                                testPassed[motorNum]++;
                                success = true;
                            } else {
                                Serial.println("✗ 校验失败");
                            }
                        }
                        break;
                    }
                }
                delay(1);
            }
            
            if (!success && rxIndex == 0) {
                Serial.println("无响应");
            }
            
            delay(500);  // 每次尝试之间等待500ms
        }
        
        // 判断电机是否可靠
        if (testPassed[motorNum] >= 2) {
            motorFound[motorNum] = true;
            Serial.print("  ✅ 电机");
            Serial.print(motorNum + 1);
            Serial.print(" 通过 (");
            Serial.print(testPassed[motorNum]);
            Serial.println("/3)");
        } else {
            Serial.print("  ❌ 电机");
            Serial.print(motorNum + 1);
            Serial.print(" 失败 (");
            Serial.print(testPassed[motorNum]);
            Serial.println("/3)");
        }
        
        Serial.println();
        delay(1000);  // 电机之间等待1秒
    }
    
    // 汇总结果
    Serial.println("═════════════════════════════════════════");
    Serial.println("扫描结果汇总:");
    Serial.println();
    
    int foundCount = 0;
    for (int i = 0; i < 4; i++) {
        Serial.print("  电机");
        Serial.print(i + 1);
        Serial.print(" (0x");
        Serial.print(testAddresses[i], HEX);
        Serial.print("): ");
        
        if (motorFound[i]) {
            Serial.print("✅ 可靠响应 (");
            Serial.print(testPassed[i]);
            Serial.println("/3)");
            foundCount++;
        } else {
            Serial.print("❌ 不稳定或无响应 (");
            Serial.print(testPassed[i]);
            Serial.println("/3)");
        }
    }
    
    Serial.println();
    Serial.print("找到 ");
    Serial.print(foundCount);
    Serial.println("/4 个可靠的电机");
    Serial.println("═════════════════════════════════════════");
    Serial.println();
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
 * 发送并接收
 */
bool sendReceive(uint8_t* tx, int txLen, uint8_t* rx, int rxLen, bool verbose) {
    if (verbose) {
        Serial.print("  发送: ");
        printHex(tx, txLen);
    }
    
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
    uint8_t targetAddr = tx[0];
    
    while (millis() - startTime < 3000) {  // 改为3000ms超时
        if (ServoSerial.available()) {
            uint8_t byte = ServoSerial.read();
            
            // 第一个字节必须是从机地址
            if (rxIndex == 0 && byte != targetAddr) {
                continue;
            }
            
            rx[rxIndex++] = byte;
            
            // 收够了
            if (rxIndex >= rxLen) {
                // 验证校验和
                uint8_t calcChecksum = calculateChecksum(rx, rxLen - 1);
                uint8_t recvChecksum = rx[rxLen - 1];
                
                if (verbose) {
                    Serial.print("  收到: ");
                    printHex(rx, rxLen);
                }
                
                if (calcChecksum == recvChecksum) {
                    if (verbose) Serial.println("  ✓ 校验成功");
                    return true;
                } else {
                    if (verbose) Serial.println("  ✗ 校验失败");
                    return false;
                }
            }
        }
        delay(1);
    }
    
    if (rxIndex > 0) {
        if (verbose) {
            Serial.print("  收到（不完整）: ");
            printHex(rx, rxIndex);
        }
    } else {
        if (verbose) Serial.println("  ✗ 超时，无响应");
    }
    
    return false;
}

/**
 * 使能单个电机（带重试机制）
 */
void enableMotor(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    Serial.print("使能电机");
    Serial.println(motorNum);
    
    uint8_t addr = addresses[motorNum - 1];
    
    // 重试最多3次
    for (int attempt = 1; attempt <= 3; attempt++) {
        if (attempt > 1) {
            Serial.print("  重试 ");
            Serial.print(attempt);
            Serial.println("/3...");
            delay(100);  // 重试前等待
        }
        
        txBuffer[0] = addr;
        txBuffer[1] = CMD_SET_ENABLE_STATE;
        txBuffer[2] = 0x01;
        txBuffer[3] = calculateChecksum(txBuffer, 3);
        
        if (sendReceive(txBuffer, 4, rxBuffer, 3, attempt == 1)) {  // 只有第一次打印详细信息
            if (rxBuffer[1] == 1) {
                Serial.println("  ✓ 使能成功");
                motor_enabled[motorNum - 1] = true;
                return;  // 成功，退出
            }
        }
    }
    
    // 3次都失败
    Serial.println("  ✗ 使能失败（3次尝试后）");
    motor_enabled[motorNum - 1] = false;
}

/**
 * 使能所有电机
 */
void enableAllMotors() {
    Serial.println("使能所有电机...");
    for (int i = 1; i <= 4; i++) {
        enableMotor(i);
        delay(100);
    }
    Serial.println("✓ 所有电机已使能");
}

/**
 * 失能单个电机（带重试机制）
 */
void disableMotor(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    Serial.print("失能电机");
    Serial.println(motorNum);
    
    uint8_t addr = addresses[motorNum - 1];
    
    // 重试最多3次
    for (int attempt = 1; attempt <= 3; attempt++) {
        if (attempt > 1) {
            Serial.print("  重试 ");
            Serial.print(attempt);
            Serial.println("/3...");
            delay(100);  // 重试前等待
        }
        
        txBuffer[0] = addr;
        txBuffer[1] = CMD_SET_ENABLE_STATE;
        txBuffer[2] = 0x00;  // 0x00 = 失能（断电）
        txBuffer[3] = calculateChecksum(txBuffer, 3);
        
        if (sendReceive(txBuffer, 4, rxBuffer, 3, attempt == 1)) {  // 只有第一次打印详细信息
            // 文档：修改成功返回 0xe0 0x01 rCHK
            if (rxBuffer[1] == 1) {
                Serial.println("  ✓ 失能成功（可手动转动）");
                motor_enabled[motorNum - 1] = false;
                return;  // 成功，退出
            }
        }
    }
    
    // 3次都失败
    Serial.println("  ✗ 失能失败（3次尝试后）");
}

/**
 * 失能所有电机
 */
void disableAllMotors() {
    Serial.println("失能所有电机...");
    for (int i = 1; i <= 4; i++) {
        disableMotor(i);
        delay(100);
    }
    Serial.println("✓ 所有电机已失能（可手动转动）");
}

/**
 * 停止单个电机
 */
void stopMotor(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    Serial.print("停止电机");
    Serial.println(motorNum);
    
    uint8_t addr = addresses[motorNum - 1];
    txBuffer[0] = addr;
    txBuffer[1] = CMD_SET_STOP_MOTOR;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    // 快速发送模式：不等待确认，立即停止
    // 清空接收缓冲区
    while (ServoSerial.available()) {
        ServoSerial.read();
    }
    
    // 直接发送停止命令
    ServoSerial.write(txBuffer, 3);
    ServoSerial.flush();
    Serial.println("  → 停止命令已发送");
}

/**
 * 停止所有电机（真正同时停止）
 * 
 * 策略：先快速发送所有命令，然后再打印调试信息
 * 避免Serial.print延迟影响发送速度
 */
void stopAllMotors() {
    Serial.println("紧急停止所有电机...");
    
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    unsigned long sendTimes[4];  // 记录每个命令的发送时间
    
    unsigned long startTime = micros();
    
    // 第一步：快速发送所有停止命令（无调试输出，避免延迟）
    for (int i = 0; i < 4; i++) {
        sendTimes[i] = micros();  // 记录时间
        
        txBuffer[0] = addresses[i];
        txBuffer[1] = CMD_SET_STOP_MOTOR;
        txBuffer[2] = calculateChecksum(txBuffer, 2);
        
        ServoSerial.write(txBuffer, 3);
    }
    
    ServoSerial.flush();  // 确保所有数据发送完毕
    
    unsigned long totalTime = micros() - startTime;
    
    // 第二步：现在安全地打印调试信息（不影响发送速度）
    for (int i = 0; i < 4; i++) {
        Serial.print("  [");
        Serial.print(sendTimes[i] - startTime);
        Serial.print("μs] 发送停止到电机");
        Serial.print(i + 1);
        Serial.print(" (0x");
        Serial.print(addresses[i], HEX);
        Serial.println(")");
    }
    
    Serial.print("✓ 所有停止命令已发送，总耗时: ");
    Serial.print(totalTime);
    Serial.println("μs");
}

/**
 * 运动单个电机
 */
void moveMotor(uint8_t motorNum, uint8_t dir, uint8_t speed) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    Serial.print("电机");
    Serial.print(motorNum);
    Serial.print(": ");
    Serial.print(dir == 0 ? "正向" : "反向");
    Serial.print(", 速度=");
    Serial.println(speed);
    
    uint8_t addr = addresses[motorNum - 1];
    if (speed > 127) speed = 127;
    
    // 根据文档：[地址] [0xF6] [方向] [速度] [加速度] [校验]
    // 方向：0=CW正向, 1=CCW反向
    // 速度：0-127
    // 加速度：0-255 (0表示使用默认值)
    txBuffer[0] = addr;
    txBuffer[1] = CMD_SET_RUN_CONTINUOUS;  // 0xF6
    txBuffer[2] = dir;                     // 方向
    txBuffer[3] = speed;                   // 速度
    txBuffer[4] = 0;                       // 加速度(0=默认)
    txBuffer[5] = calculateChecksum(txBuffer, 5);
    
    // 快速发送模式：不等待确认回复
    while (ServoSerial.available()) {
        ServoSerial.read();
    }
    
    ServoSerial.write(txBuffer, 6);
    ServoSerial.flush();
    Serial.println("  → 命令已发送");
    
    delay(10);
}

/**
 * 所有电机同时运动（快速版本 - 几乎同时启动）
 */
void moveAllMotors(uint8_t dir, uint8_t speed) {
    Serial.print("所有电机");
    Serial.print(dir == 0 ? "正向" : "反向");
    Serial.print("运动, 速度=");
    Serial.println(speed);
    
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (speed > 127) speed = 127;
    uint8_t value = (dir == 1 ? 0x80 : 0x00) | speed;
    
    // 快速连续发送命令到所有电机，无延迟
    for (int i = 0; i < 4; i++) {
        txBuffer[0] = addresses[i];
        txBuffer[1] = CMD_SET_RUN_CONTINUOUS;
        txBuffer[2] = value;
        txBuffer[3] = calculateChecksum(txBuffer, 3);
        
        ServoSerial.write(txBuffer, 4);
        // 不使用flush，让命令立即发送
    }
    
    ServoSerial.flush();  // 确保所有数据发送完毕
    
    Serial.println("✓ 运动命令已发送到所有电机 (同步启动)");
}

/**
 * 读取电机编码器
 */
void readEncoder(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    uint8_t addr = addresses[motorNum - 1];
    txBuffer[0] = addr;
    txBuffer[1] = CMD_GET_ENCODER_VALUES;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 8)) {
        int32_t carrier = ((int32_t)rxBuffer[1] << 24) | ((int32_t)rxBuffer[2] << 16) |
                          ((int32_t)rxBuffer[3] << 8) | rxBuffer[4];
        uint16_t value = ((uint16_t)rxBuffer[5] << 8) | rxBuffer[6];
        float motorAngle = (value * 360.0) / 65536.0;  // 电机轴角度
        
        // 获取减速比
        float gearRatio = GEAR_RATIO[motorNum - 1];
        
        // 计算输出轴的角度和圈数
        float outputAngle = motorAngle / gearRatio;  // 输出轴当前角度（0-360°）
        float outputTurns = (carrier + (motorAngle / 360.0)) / gearRatio;  // 输出轴总圈数
        float totalAngle = outputTurns * 360.0;  // 总角度（绝对位置）
        
        // 计算相对零点的角度
        float relativeAngle = totalAngle - zero_angles[motorNum - 1];
        
        Serial.print("  电机");
        Serial.print(motorNum);
        
        if (gearRatio > 1.0) {
            // 有减速器
            Serial.print(" [1:");
            Serial.print((int)gearRatio);
            Serial.print("减速] 位置: ");
            Serial.print(relativeAngle, 2);
            Serial.print("° (相对零点)");
            
            Serial.print("  [物理: ");
            Serial.print(outputAngle, 2);
            Serial.print("° (");
            Serial.print(outputTurns, 3);
            Serial.print("圈)]");
            
            Serial.print("  [电机: ");
            Serial.print(motorAngle, 2);
            Serial.print("° (");
            Serial.print(carrier);
            Serial.print("圈)]");
        } else {
            // 无减速器
            Serial.print(" 位置: ");
            Serial.print(relativeAngle, 2);
            Serial.print("° (相对零点)  [物理: ");
            Serial.print(motorAngle, 2);
            Serial.print("° (圈数: ");
            Serial.print(carrier);
            Serial.print(")]");
        }
        Serial.println();
    }
}

/**
 * 读取所有编码器
 */
void readAllEncoders() {
    Serial.println("读取所有编码器...");
    for (int i = 1; i <= 4; i++) {
        readEncoder(i);
        delay(100);
    }
}

/**
 * 获取当前角度（输出轴）
 * 返回相对于零点的角度
 * 带重试机制
 */
float getCurrentAngle(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return 0.0;
    
    uint8_t addr = addresses[motorNum - 1];
    
    // 清空串口缓冲区，避免旧数据干扰
    while (ServoSerial.available()) {
        ServoSerial.read();
    }
    delay(50);  // 等待电机稳定
    
    // 重试最多3次
    for (int attempt = 0; attempt < 3; attempt++) {
        // 读取编码器
        txBuffer[0] = addr;
        txBuffer[1] = CMD_GET_ENCODER_VALUES;
        txBuffer[2] = calculateChecksum(txBuffer, 2);
        
        if (sendReceive(txBuffer, 3, rxBuffer, 8, false)) {  // 改回 false 减少输出
            // 正确读取 carrier (4字节 int32)
            int32_t carrier = ((int32_t)rxBuffer[1] << 24) | ((int32_t)rxBuffer[2] << 16) |
                              ((int32_t)rxBuffer[3] << 8) | rxBuffer[4];
            uint16_t value = ((uint16_t)rxBuffer[5] << 8) | rxBuffer[6];
            float motorAngle = (value * 360.0) / 65536.0;
            
            // 计算输出轴角度
            float gearRatio = GEAR_RATIO[motorNum - 1];
            float outputAngle = motorAngle / gearRatio;
            float outputTurns = (carrier + (motorAngle / 360.0)) / gearRatio;
            float totalAngle = outputTurns * 360.0;
            
            // 相对于零点
            return totalAngle - zero_angles[motorNum - 1];
        }
        
        // 失败，延迟后重试
        delay(100);  // 增加到100ms
    }
    
    // 3次都失败，打印警告
    Serial.print("  ⚠ 读取电机");
    Serial.print(motorNum);
    Serial.println("位置失败（3次尝试）");
    
    return 0.0;  // 实在没办法，返回0
}

/**
 * 设置当前位置为零点
 * 改进版：同时发送0x91给电机，实现软硬件同步回零
 */
void setZeroPosition(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    uint8_t addr = addresses[motorNum - 1];
    
    Serial.print("设置电机");
    Serial.print(motorNum);
    Serial.println("零点...");
    
    // 1. 发送 0x91 Set 0 命令给电机 (设置自动回零的零点)
    // 格式: [Addr] [0x91] [00] [Chk]
    // 加上 0x90 设置回零模式为 02 (就近模式) 或 01 (方向模式)
    // 这里我们只设零点
    txBuffer[0] = addr;
    txBuffer[1] = 0x91;
    txBuffer[2] = 0x00; // 填充
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    ServoSerial.write(txBuffer, 4);
    delay(100);
    
    // 清空缓冲区
    while (ServoSerial.available()) {
        ServoSerial.read();
    }
    
    // 2. 更新软件层面的零点
    // 因为电机内部已经置零，所以软件偏移量也设为0即可
    // 但为了确认电机真的置零了，我们读一下
    
    delay(100);
    
    // 先把软件偏移设为0，这样getCurrentAngle读出来的就是电机原始角度
    zero_angles[motorNum - 1] = 0.0;
    target_angles[motorNum - 1] = 0.0;
    
    // 读取当前角度 (此时 zero_angles 已经是0，所以读出来的是绝对角度)
    float currentAngle = getCurrentAngle(motorNum); 
    
    if (!isnan(currentAngle)) {
        // 这里的 currentAngle 已经是绝对角度了
        Serial.print("  ✓ 零点已同步. 当前绝对位置: ");
        Serial.print(currentAngle, 2);
        Serial.println("°");
        
        // 如果绝对位置接近0，说明硬件置零成功
        if (abs(currentAngle) < 1.0) {
            Serial.println("  ✓ 硬件置零成功 (支持0x91命令)");
        } else {
            Serial.println("  ⚠ 硬件置零未生效 (仅软件置零)");
            // 如果硬件没置零，我们需要把当前的绝对角度记下来作为偏移
            zero_angles[motorNum - 1] = currentAngle;
        }
    } else {
        Serial.println("  ✗ 读取位置失败，零点可能未正确设置");
    }
}

/**
 * 设置所有电机零点
 */
void setAllZeroPositions() {
    Serial.println("设置所有电机零点...");
    for (int i = 1; i <= 4; i++) {
        setZeroPosition(i);
        delay(100);
    }
    Serial.println("✓ 所有零点已设置");
}

/**
 * 回零命令 (0x94) - 电机自动回到设定的零点
 * 需要先用 setzero 设置过零点
 */
void gotoZero(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    uint8_t addr = addresses[motorNum - 1];
    
    Serial.print("电机");
    Serial.print(motorNum);
    Serial.println(" 执行回零 (0x94)...");
    
    // 根据文档：发送 e0 94 00 tCHK，回到零点
    txBuffer[0] = addr;
    txBuffer[1] = CMD_GOTO_ZERO;  // 0x94
    txBuffer[2] = 0x00;           // 填充
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    ServoSerial.write(txBuffer, 4);
    delay(50);
    
    // 等待回复
    if (ServoSerial.available() >= 3) {
        ServoSerial.readBytes(rxBuffer, 3);
        if (rxBuffer[1] == 0x01) {
            Serial.println("  ✓ 回零命令已发送，电机正在移动...");
        }
    }
}

/**
 * 设置工作模式 (0x82)
 * mode: 0=CR_OPEN(开环), 1=CR_vFOC(闭环STD/DIR), 2=CR_UART(闭环UART)
 */
void setWorkMode(uint8_t motorNum, uint8_t mode) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    uint8_t addr = addresses[motorNum - 1];
    
    Serial.print("设置电机");
    Serial.print(motorNum);
    Serial.print(" 工作模式: ");
    
    const char* modeNames[] = {"CR_OPEN(开环)", "CR_vFOC(闭环STD/DIR)", "CR_UART(闭环UART)"};
    if (mode <= 2) {
        Serial.println(modeNames[mode]);
    } else {
        Serial.println("未知模式");
        return;
    }
    
    // 根据文档：发送 e0 82 [模式] tCHK
    txBuffer[0] = addr;
    txBuffer[1] = CMD_SET_WORK_MODE;  // 0x82
    txBuffer[2] = mode;
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    // 打印发送的命令
    Serial.print("  发送: ");
    for (int i = 0; i < 4; i++) {
        if (txBuffer[i] < 0x10) Serial.print("0");
        Serial.print(txBuffer[i], HEX);
        Serial.print(" ");
    }
    Serial.println();
    
    // 清空缓冲区
    while (ServoSerial.available()) {
        ServoSerial.read();
    }
    
    ServoSerial.write(txBuffer, 4);
    delay(150);
    
    // 等待回复
    if (ServoSerial.available() >= 3) {
        ServoSerial.readBytes(rxBuffer, 3);
        
        Serial.print("  收到: ");
        for (int i = 0; i < 3; i++) {
            if (rxBuffer[i] < 0x10) Serial.print("0");
            Serial.print(rxBuffer[i], HEX);
            Serial.print(" ");
        }
        Serial.println();
        
        // 检查校验
        uint8_t expectedChecksum = calculateChecksum(rxBuffer, 2);
        if (expectedChecksum == rxBuffer[2]) {
            Serial.println("  ✓ 校验成功");
            if (rxBuffer[1] == 0x01) {
                Serial.println("  ✓ 模式设置成功");
                Serial.println("  ⚠ 注意：模式切换后，电机可能需要重新上电或重启才能完全生效");
            } else if (rxBuffer[1] == 0x00) {
                Serial.println("  ✗ 模式设置失败 (电机拒绝)");
                Serial.println("  可能原因：");
                Serial.println("    1. 电机固件不支持此模式");
                Serial.println("    2. 需要先失能电机");
                Serial.println("    3. 电机型号不支持UART模式");
            } else {
                Serial.print("  ⚠ 未知状态码: 0x");
                Serial.println(rxBuffer[1], HEX);
            }
        } else {
            Serial.println("  ✗ 校验失败");
        }
    } else {
        Serial.println("  ⚠ 无回复 (电机可能不支持此命令)");
    }
}

/**
 * 读取累计脉冲数 (0x33)
 */
void readPulseCount(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    uint8_t addr = addresses[motorNum - 1];
    
    // 根据文档：发送 e0 33 tCHK，读取累计脉冲
    // 返回：e0, int32_t 类型的累计脉冲值和校验值 tCHK
    txBuffer[0] = addr;
    txBuffer[1] = CMD_GET_PULSE_COUNT;  // 0x33
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 6, false)) {
        // 读取 int32_t (4字节)
        int32_t pulseCount = ((int32_t)rxBuffer[1] << 24) | 
                             ((int32_t)rxBuffer[2] << 16) |
                             ((int32_t)rxBuffer[3] << 8) | 
                             rxBuffer[4];
        
        Serial.print("电机");
        Serial.print(motorNum);
        Serial.print(" 累计脉冲: ");
        Serial.println(pulseCount);
    } else {
        Serial.println("  ✗ 读取失败");
    }
}

/**
 * 读取实时位置 (0x36) - 返回0-65535的编码器值
 */
void readRealtimePosition(uint8_t motorNum) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) return;
    
    uint8_t addr = addresses[motorNum - 1];
    
    // 根据文档：发送 e0 36 tCHK，读取实时位置
    // 返回：e0, uint16_t 类型的闭环电机的实时位置和校验值 tCHK
    txBuffer[0] = addr;
    txBuffer[1] = CMD_GET_REALTIME_POSITION;  // 0x36
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 4, false)) {
        // 读取 uint16_t (2字节)
        uint16_t position = ((uint16_t)rxBuffer[1] << 8) | rxBuffer[2];
        float angle = (position * 360.0) / 65536.0;
        
        Serial.print("电机");
        Serial.print(motorNum);
        Serial.print(" 实时位置: ");
        Serial.print(position);
        Serial.print(" (");
        Serial.print(angle, 2);
        Serial.println("°)");
    } else {
        Serial.println("  ✗ 读取失败");
    }
}

/**
 * 精确移动到指定角度（使用0xFD位置模式）
 * 这是推荐的方式 - 电机硬件闭环控制
 */
void moveToAnglePrecise(uint8_t motorNum, float targetAngle, int speed) {
    uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
    
    if (motorNum < 1 || motorNum > 4) {
        Serial.println("✗ 无效的电机编号");
        return;
    }
    
    Serial.print("\n电机");
    Serial.print(motorNum);
    Serial.print(" 精确移动到 ");
    Serial.print(targetAngle, 1);
    Serial.println("° (0xFD位置闭环)");
    
    uint8_t addr = addresses[motorNum - 1];
    
    // 1. 读取当前角度，计算误差
    float currentAngle = getCurrentAngle(motorNum);
    if (isnan(currentAngle)) {
        Serial.println("  ✗ 无法读取起始角度");
        return;
    }
    
    float error = targetAngle - currentAngle;
    if (abs(error) < 0.5) {
        Serial.println("  ✓ 已在目标位置");
        return;
    }
    
    Serial.print("  误差: ");
    Serial.print(error, 1);
    Serial.println("°");
    
    // 2. 计算脉冲数
    // 回滚到"能动"的版本，并调整系数
    // 上次测试：系数2.0 -> 90度跑了113.7度
    // 说明系数太大。应为 2.0 * (90/113.7) ≈ 1.58
    float gearRatio = GEAR_RATIO[motorNum - 1];
    float correctionFactor = 1.58; 
    
    // 脉冲计算公式
    // 3200是16细分下的每圈脉冲数
    int32_t totalPulses = (int32_t)(abs(error) / 360.0 * 3200.0 * gearRatio * correctionFactor);
    
    // 限制脉冲数 (虽然那个版本是16位，但我们还是限制一下)
    if (totalPulses > 65535) totalPulses = 65535;
    if (totalPulses == 0) return;
    
    // 3. 准备命令包 - 回滚到"能动"的 8字节格式
    // [Addr] [0xFD] [Dir] [Speed] [PulseH] [PulseL] [Acc] [Chk]
    
    uint8_t dir = (error > 0) ? 0 : 1;  // 0=正向, 1=反向
    
    // 限制速度
    if (speed > 127) speed = 127;
    if (speed < 1) speed = 20;
    
    // 默认加速度
    uint8_t acceleration = 0; // 0=默认
    
    txBuffer[0] = addr;
    txBuffer[1] = 0xFD;
    txBuffer[2] = dir;          // 方向单独一个字节
    txBuffer[3] = speed;        // 速度单独一个字节
    txBuffer[4] = (totalPulses >> 8) & 0xFF;  // 脉冲高8位
    txBuffer[5] = totalPulses & 0xFF;         // 脉冲低8位
    txBuffer[6] = acceleration; // 加速度
    txBuffer[7] = calculateChecksum(txBuffer, 7);
    
    Serial.print("  发送脉冲: ");
    Serial.print(totalPulses);
    Serial.print(" (方向: ");
    Serial.print(dir == 0 ? "正" : "反");
    Serial.print(", 速度: ");
    Serial.print(speed);
    Serial.println(")");
    
    // 打印原始命令
    Serial.print("  命令: ");
    for (int i = 0; i < 8; i++) {
        if (txBuffer[i] < 0x10) Serial.print("0");
        Serial.print(txBuffer[i], HEX);
        Serial.print(" ");
    }
    Serial.println();
    
    // 发送命令（8字节）
    ServoSerial.write(txBuffer, 8);
    
    // 4. 等待运动完成信号 (0x02)
    // 文档：开始返回 0x01, 完成返回 0x02
    Serial.println("  等待电机执行...");
    
    unsigned long startTime = millis();
    bool isFinished = false;
    bool hasStarted = false;
    
    // 根据脉冲数估算一个最大超时时间，防止死等
    unsigned long timeoutMs = (totalPulses / 100) * 100 + 2000; 
    if (timeoutMs < 2000) timeoutMs = 2000;
    
    while (millis() - startTime < timeoutMs) {
        if (ServoSerial.available() >= 3) {
            // 简单的滑动窗口查找或者是直接读取
            // 这里假设回复也是标准格式 [Addr] [xx] [Chk]
            uint8_t respAddr = ServoSerial.read();
            if (respAddr == addr) {
                uint8_t status = ServoSerial.read();
                uint8_t chk = ServoSerial.read();
                
                // 简单的校验检查
                if ((respAddr + status) % 256 != chk) {
                   // 校验失败，忽略
                   continue;
                }
                
                if (status == 0x01) {
                    if (!hasStarted) {
                        Serial.println("  → 运动开始 (0x01)");
                        hasStarted = true;
                    }
                }
                else if (status == 0x02) {
                    Serial.println("  ✓ 运动完成 (0x02)");
                    isFinished = true;
                    break;
                }
                else if (status == 0x00) {
                     Serial.println("  ✗ 命令失败 (0x00)");
                     break;
                }
            }
        }
        delay(5);
    }
    
    if (!isFinished) {
        Serial.println("  ⚠ 等待超时 (可能是运动时间过长或未收到完成信号)");
    }
    
    // 最终检查
    float finalAngle = getCurrentAngle(motorNum);
    Serial.print("  最终: "); Serial.print(finalAngle, 1);
    Serial.print("° 误差: "); Serial.println(targetAngle - finalAngle, 1);
}

/**
 * 移动到指定角度（相对于零点）
 * 改进版本 - 基于时间估算 + 安全检查
 * 注意：不推荐使用此方法，请使用 moveToAnglePrecise
 */
void moveToAngle(uint8_t motorNum, float targetAngle, int speed) {
    if (motorNum < 1 || motorNum > 4) {
        Serial.println("✗ 无效的电机编号");
        return;
    }
    
    Serial.print("\n电机");
    Serial.print(motorNum);
    Serial.print(" 移动到 ");
    Serial.print(targetAngle, 1);
    Serial.println("°");
    
    // 读取当前角度（带重试）
    float currentAngle = getCurrentAngle(motorNum);
    
    // 检查读取是否失败
    // 如果目标不是0，但读取到0，很可能是读取失败
    if (currentAngle == 0.0 && abs(targetAngle) > 5.0) {
        // 再读一次确认
        Serial.println("  ⚠ 第一次读取可能失败，重试...");
        delay(200);
        currentAngle = getCurrentAngle(motorNum);
        
        if (currentAngle == 0.0) {
            Serial.println("  ✗ 编码器读取失败，无法安全移动");
            Serial.println("  提示：请先用 'pos1' 命令检查电机是否正常通信");
            return;  // 安全起见，不移动
        }
    }
    
    float error = targetAngle - currentAngle;
    
    Serial.print("  当前: ");
    Serial.print(currentAngle, 1);
    Serial.print("° → 目标: ");
    Serial.print(targetAngle, 1);
    Serial.print("° (误差: ");
    Serial.print(error, 1);
    Serial.println("°)");
    
    // 如果已经很接近，不移动
    if (abs(error) < 3.0) {
        Serial.println("  ✓ 已在目标位置附近");
        stopMotor(motorNum);
        return;
    }
    
    // 安全检查：误差太大可能有问题
    if (abs(error) > 360.0) {
        Serial.println("  ✗ 误差过大 (>360°)，可能零点未设置或读取错误");
        return;
    }
    
    // 【智能修正算法】
    // 不再一次性计算，而是"转-停-测-修"的循环
    int maxAttempts = 8;  // 最大尝试次数
    int attempts = 0;
    
    while (attempts < maxAttempts) {
        // 1. 读取当前角度
        float currentAngle = getCurrentAngle(motorNum);
        if (isnan(currentAngle)) {
            Serial.println("  ✗ 角度读取失败，停止");
            break;
        }
        
        // 2. 计算误差
        float error = targetAngle - currentAngle;
        
        // 3. 判断是否到达
        if (abs(error) < 2.5) {  // 允许2.5度误差
            Serial.println("  ✓ 已到达目标");
            break;
        }
        
        attempts++;
        Serial.print("  [修正"); 
        Serial.print(attempts); 
        Serial.print("] 当前:"); 
        Serial.print(currentAngle, 1); 
        Serial.print("° 误差:"); 
        Serial.print(error, 1);
        
        // 4. 动态计算移动时间
        // 基础速度：约10ms/度
        int moveTimeMs = (int)(abs(error) * 10.0);
        
        // 5. 智能时间限制
        if (moveTimeMs > 600) moveTimeMs = 600;  // 单次最多跑600ms，防止大幅过头
        if (moveTimeMs < 40) moveTimeMs = 40;    // 最小脉冲40ms，防止电机没劲不动
        
        // 如果误差非常小(<5度)，给非常短的点动
        if (abs(error) < 5.0) moveTimeMs = 25;
        
        Serial.print("° → 移动 "); 
        Serial.print(moveTimeMs); 
        Serial.println("ms");
        
        // 6. 执行移动
        uint8_t dir = (error > 0) ? 0 : 1;
        moveMotor(motorNum, dir, speed);
        delay(moveTimeMs);
        stopMotor(motorNum);
        
        // 7. 等待电机停稳 (关键!)
        delay(150);
    }
    
    if (attempts >= maxAttempts) {
        Serial.println("  ⚠ 达到最大修正次数，停止");
    }
    
    // 清空串口缓冲区，避免旧数据干扰
    while (ServoSerial.available()) {
        ServoSerial.read();
    }
    delay(100);  // 额外等待编码器稳定
    
    // 读取最终位置
    float finalAngle = getCurrentAngle(motorNum);
    float finalError = targetAngle - finalAngle;
    
    Serial.print("  最终: ");
    Serial.print(finalAngle, 1);
    Serial.print("° (误差: ");
    Serial.print(finalError, 1);
    Serial.println("°)");
    
    if (abs(finalError) < 10.0) {
        Serial.println("  ✓ 到达目标位置");
    } else {
        Serial.println("  ⚠ 未完全到达目标，可能需要调整速度或时间估算");
    }
}

/**
 * 处理命令
 */
void handleCommand(String cmd) {
    Serial.print("\n→ 命令: ");
    Serial.println(cmd);
    Serial.println();
    
    // 使能命令
    if (cmd == "enable" || cmd == "en") {
        enableAllMotors();
    }
    else if (cmd.startsWith("en")) {
        int num = cmd.substring(2).toInt();
        if (num >= 1 && num <= 4) enableMotor(num);
    }
    
    // 失能命令
    else if (cmd == "disable" || cmd == "dis") {
        disableAllMotors();
    }
    else if (cmd.startsWith("dis")) {
        int num = cmd.substring(3).toInt();
        if (num >= 1 && num <= 4) disableMotor(num);
    }
    
    // 停止命令
    else if (cmd == "stop" || cmd == "s") {
        stopAllMotors();
    }
    else if (cmd.startsWith("stop")) {
        int num = cmd.substring(4).toInt();
        if (num >= 1 && num <= 4) stopMotor(num);
    }
    
    // 运动命令 - 所有电机
    else if (cmd.startsWith("allf")) {  // all motors forward
        int speed = cmd.substring(4).toInt();
        if (speed == 0) speed = 50;
        moveAllMotors(0, speed);
    }
    else if (cmd.startsWith("allr")) {  // all motors reverse
        int speed = cmd.substring(4).toInt();
        if (speed == 0) speed = 50;
        moveAllMotors(1, speed);
    }
    
    // 运动命令 - 单个电机
    else if (cmd.startsWith("m1f")) {  // motor1 forward
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(1, 0, speed);
    }
    else if (cmd.startsWith("m1r")) {  // motor1 reverse
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(1, 1, speed);
    }
    else if (cmd.startsWith("m2f")) {
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(2, 0, speed);
    }
    else if (cmd.startsWith("m2r")) {
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(2, 1, speed);
    }
    else if (cmd.startsWith("m3f")) {
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(3, 0, speed);
    }
    else if (cmd.startsWith("m3r")) {
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(3, 1, speed);
    }
    else if (cmd.startsWith("m4f")) {
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(4, 0, speed);
    }
    else if (cmd.startsWith("m4r")) {
        int speed = cmd.substring(3).toInt();
        if (speed == 0) speed = 50;
        moveMotor(4, 1, speed);
    }
    
    // 查询命令
    else if (cmd == "pos" || cmd == "position") {
        readAllEncoders();
    }
    else if (cmd.startsWith("pos")) {
        int num = cmd.substring(3).toInt();
        if (num >= 1 && num <= 4) readEncoder(num);
    }
    
    // 零点设置命令
    else if (cmd == "setzero") {
        setAllZeroPositions();
    }
    else if (cmd.startsWith("setzero")) {
        int num = cmd.substring(7).toInt();
        if (num >= 1 && num <= 4) setZeroPosition(num);
    }
    
    // 设置工作模式 - mode1:2 (设置电机1为CR_UART模式)
    else if (cmd.startsWith("mode")) {
        int colonPos = cmd.indexOf(':');
        if (colonPos > 0) {
            int motorNum = cmd.substring(4, colonPos).toInt();
            int mode = cmd.substring(colonPos + 1).toInt();
            
            if (motorNum >= 1 && motorNum <= 4 && mode >= 0 && mode <= 2) {
                // 建议：先失能再设置模式
                Serial.println("提示：建议先失能电机再切换模式");
                Serial.print("是否需要先失能? 输入 dis");
                Serial.print(motorNum);
                Serial.println(" 然后重试");
                delay(1000);
                
                setWorkMode(motorNum, mode);
            } else {
                Serial.println("✗ 格式: mode1:2 (电机1设为CR_UART模式)");
                Serial.println("  模式: 0=开环, 1=闭环STD/DIR, 2=闭环UART");
            }
        }
    }
    
    // 设置加速度命令 - setacc1:50
    else if (cmd.startsWith("setacc")) {
        int colonPos = cmd.indexOf(':');
        if (colonPos > 0) {
            int motorNum = cmd.substring(6, colonPos).toInt();
            int acc = cmd.substring(colonPos + 1).toInt();
            
            if (motorNum >= 1 && motorNum <= 4) {
                uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
                uint8_t addr = addresses[motorNum - 1];
                
                // 限制 ACC 范围
                if (acc < 0) acc = 0;
                if (acc > 255) acc = 255;
                
                // 根据文档：[地址] [0xA4] [填充] [ACC值] [校验]
                txBuffer[0] = addr;
                txBuffer[1] = CMD_SET_ACCELERATION;  // 0xA4
                txBuffer[2] = 0x00;                  // 填充
                txBuffer[3] = (uint8_t)acc;
                txBuffer[4] = calculateChecksum(txBuffer, 4);
                
                ServoSerial.write(txBuffer, 5);
                Serial.print("电机"); Serial.print(motorNum); Serial.print(" 加速度设为: "); Serial.println(acc);
            }
        }
    }
    
    // 回零命令 - home1
    else if (cmd.startsWith("home")) {
        int num = cmd.substring(4).toInt();
        if (num >= 1 && num <= 4) {
            gotoZero(num);
        } else if (num == 0 || cmd == "home") {
            Serial.println("所有电机回零...");
            for (int i = 1; i <= 4; i++) {
                gotoZero(i);
                delay(500);
            }
        }
    }
    
    // 读取累计脉冲 - pulse1
    else if (cmd.startsWith("pulse")) {
        int num = cmd.substring(5).toInt();
        if (num >= 1 && num <= 4) {
            readPulseCount(num);
        }
    }
    
    // 读取实时位置 - realpos1
    else if (cmd.startsWith("realpos")) {
        int num = cmd.substring(7).toInt();
        if (num >= 1 && num <= 4) {
            readRealtimePosition(num);
        }
    }

    // 测试0xFD命令 - 固定脉冲数
    else if (cmd.startsWith("testfd")) {
        int motorNum = cmd.substring(6).toInt();
        if (motorNum >= 1 && motorNum <= 4) {
            uint8_t addresses[] = {MOTOR1_ADDR, MOTOR2_ADDR, MOTOR3_ADDR, MOTOR4_ADDR};
            uint8_t addr = addresses[motorNum - 1];
            
            Serial.println("\n【测试0xFD命令 - 1000脉冲】");
            
            // 尝试最简单的命令：1000脉冲，正向，速度50
            txBuffer[0] = addr;
            txBuffer[1] = 0xFD;
            txBuffer[2] = 0x00;  // 方向：正向
            txBuffer[3] = 50;    // 速度
            txBuffer[4] = 0x03;  // 脉冲高字节 (1000 = 0x03E8)
            txBuffer[5] = 0xE8;  // 脉冲低字节
            txBuffer[6] = 50;    // 加速度
            txBuffer[7] = calculateChecksum(txBuffer, 7);
            
            Serial.print("发送: ");
            for (int i = 0; i < 8; i++) {
                if (txBuffer[i] < 0x10) Serial.print("0");
                Serial.print(txBuffer[i], HEX);
                Serial.print(" ");
            }
            Serial.println();
            
            ServoSerial.write(txBuffer, 8);
            delay(100);
            
            if (ServoSerial.available() >= 3) {
                ServoSerial.readBytes(rxBuffer, 3);
                Serial.print("收到: ");
                for (int i = 0; i < 3; i++) {
                    if (rxBuffer[i] < 0x10) Serial.print("0");
                    Serial.print(rxBuffer[i], HEX);
                    Serial.print(" ");
                }
                Serial.println();
            }
            
            Serial.println("→ 电机应该转动约5.5° (1000脉冲 ÷ 65536 × 360°)");
        }
    }
    
    // 精确角度控制命令 - pgoto1:90 (使用位置模式)
    else if (cmd.startsWith("pgoto")) {
        int colonPos = cmd.indexOf(':');
        if (colonPos > 0) {
            int motorNum = cmd.substring(5, colonPos).toInt();
            float angle = cmd.substring(colonPos + 1).toFloat();
            int speed = 60;  // 默认速度（位置模式下可以稍慢）
            
            // 检查是否有速度参数 - pgoto1:90:60
            int secondColon = cmd.indexOf(':', colonPos + 1);
            if (secondColon > 0) {
                speed = cmd.substring(secondColon + 1).toInt();
            }
            
            if (motorNum >= 1 && motorNum <= 4) {
                moveToAnglePrecise(motorNum, angle, speed);
            } else {
                Serial.println("✗ 无效的电机编号 (1-4)");
            }
        } else {
            Serial.println("✗ 格式错误，使用: pgoto1:90 或 pgoto1:90:60");
        }
    }
    
    // 角度控制命令 - goto1:90 (移动电机1到90度，旧方式)
    else if (cmd.startsWith("goto")) {
        int colonPos = cmd.indexOf(':');
        if (colonPos > 0) {
            int motorNum = cmd.substring(4, colonPos).toInt();
            float angle = cmd.substring(colonPos + 1).toFloat();
            int speed = 80;  // 默认速度
            
            // 检查是否有速度参数 - goto1:90:60
            int secondColon = cmd.indexOf(':', colonPos + 1);
            if (secondColon > 0) {
                speed = cmd.substring(secondColon + 1).toInt();
            }
            
            if (motorNum >= 1 && motorNum <= 4) {
                moveToAngle(motorNum, angle, speed);
            } else {
                Serial.println("✗ 无效的电机编号 (1-4)");
            }
        } else {
            Serial.println("✗ 格式错误，使用: goto1:90 或 goto1:90:60");
        }
    }
    
    // 测试命令
    else if (cmd == "test") {
        testAllMotors();
    }
    
    // 扫描地址
    else if (cmd == "scan") {
        scanAllAddresses();
    }
    else if (cmd == "scanfast") {
        scanAllAddresses();
    }
    else if (cmd == "scanslow") {
        scanSlowAndSteady();
    }
    
    // 演示命令
    else if (cmd == "demo") {
        runDemo();
    }
    
    // 帮助
    else if (cmd == "help" || cmd == "h") {
        printHelp();
    }
    
    else {
        Serial.println("✗ 未知命令，输入 'help' 查看帮助");
    }
    
    Serial.println();
}

/**
 * 演示程序
 */
void runDemo() {
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  机械臂演示程序                           ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    
    // 使能所有电机
    Serial.println("步骤 1: 使能所有电机");
    enableAllMotors();
    delay(1000);
    
    // 电机1正向
    Serial.println("\n步骤 2: 基座旋转");
    moveMotor(1, 0, 40);
    delay(3000);
    stopMotor(1);
    delay(500);
    
    // 电机2正向
    Serial.println("\n步骤 3: 大臂抬起");
    moveMotor(2, 0, 40);
    delay(3000);
    stopMotor(2);
    delay(500);
    
    // 电机3正向
    Serial.println("\n步骤 4: 小臂伸展");
    moveMotor(3, 0, 40);
    delay(3000);
    stopMotor(3);
    delay(500);
    
    // 电机4正向
    Serial.println("\n步骤 5: 手腕转动");
    moveMotor(4, 0, 40);
    delay(3000);
    stopMotor(4);
    delay(500);
    
    // 读取位置
    Serial.println("\n步骤 6: 读取当前位置");
    readAllEncoders();
    delay(1000);
    
    // 反向回去
    Serial.println("\n步骤 7: 回到初始位置");
    moveMotor(4, 1, 40);
    delay(3000);
    stopMotor(4);
    
    moveMotor(3, 1, 40);
    delay(3000);
    stopMotor(3);
    
    moveMotor(2, 1, 40);
    delay(3000);
    stopMotor(2);
    
    moveMotor(1, 1, 40);
    delay(3000);
    stopMotor(1);
    
    Serial.println("\n✓ 演示完成！");
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
    Serial.println("║  4轴机械臂控制命令                        ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("【使能/失能/停止】");
    Serial.println("  enable     - 使能所有电机（通电锁定）");
    Serial.println("  en1        - 使能电机1");
    Serial.println("  en2        - 使能电机2");
    Serial.println("  disable    - 失能所有电机（断电可转）⭐");
    Serial.println("  dis1       - 失能电机1");
    Serial.println("  dis2       - 失能电机2");
    Serial.println("  stop       - 停止所有电机（保持通电）");
    Serial.println("  stop1      - 停止电机1");
    Serial.println();
    Serial.println("【运动控制】");
    Serial.println("  allf50     - 所有电机正向，速度50 ⭐");
    Serial.println("  allr50     - 所有电机反向，速度50 ⭐");
    Serial.println("  m1f50      - 电机1正向，速度50");
    Serial.println("  m1r50      - 电机1反向，速度50");
    Serial.println("  m2f50      - 电机2正向");
    Serial.println("  m2r50      - 电机2反向");
    Serial.println("  m3f50      - 电机3正向");
    Serial.println("  m3r50      - 电机3反向");
    Serial.println("  m4f50      - 电机4正向");
    Serial.println("  m4r50      - 电机4反向");
    Serial.println("  (速度范围: 1-127)");
    Serial.println("  ⚠ 注意：有减速器的电机，输出轴速度=电机速度÷减速比");
    Serial.println();
    Serial.println("【位置查询】");
    Serial.println("  position   - 读取所有电机位置");
    Serial.println("  pos1       - 读取电机1位置");
    Serial.println();
    Serial.println("【零点设置】⭐ 重要");
    Serial.println("  setzero    - 设置所有电机当前位置为零点");
    Serial.println("  setzero1   - 设置电机1当前位置为零点");
    Serial.println("  home1      - 电机1自动回到零点 (0x94命令)");
    Serial.println("  home       - 所有电机回零");
    Serial.println();
    Serial.println("【精确角度控制】⭐⭐ 推荐");
    Serial.println("  pgoto1:90   - 电机1精确移动到90° (0xFD位置模式) ⭐⭐");
    Serial.println("  pgoto1:-90  - 电机1精确移动到-90°");
    Serial.println("  pgoto1:0    - 电机1回到零点");
    Serial.println("  pgoto1:45:60 - 移动到45°，速度60");
    Serial.println();
    Serial.println("【高级功能】");
    Serial.println("  mode1:2     - 设置电机1为CR_UART模式 (0xFD命令必需!) ⭐");
    Serial.println("                0=开环, 1=闭环STD/DIR, 2=闭环UART");
    Serial.println("  setacc1:80  - 设置电机1加速度为80 (0-255)");
    Serial.println("  pulse1      - 读取电机1累计脉冲数 (0x33)");
    Serial.println("  realpos1    - 读取电机1实时位置 (0x36)");
    Serial.println();
    Serial.println("【角度控制 - 旧版本】");
    Serial.println("  goto1:90   - 电机1移动到90° (时间估算，不够准确)");
    Serial.println("  goto1:-90  - 电机1移动到-90°");
    Serial.println();
    Serial.println("【测试命令】");
    Serial.println("  testfd1     - 测试电机1的0xFD命令（1000脉冲）");
    Serial.println();
    Serial.println("【其他】");
    Serial.println("  test       - 测试所有电机通信");
    Serial.println("  scan       - 快速扫描所有电机地址");
    Serial.println("  scanslow   - 慢速稳定扫描 (推荐) ⭐");
    Serial.println("  demo       - 运行演示程序");
    Serial.println("  help       - 显示此帮助");
    Serial.println();
    Serial.println("提示：可以组合使用多个命令");
    Serial.println();
}
