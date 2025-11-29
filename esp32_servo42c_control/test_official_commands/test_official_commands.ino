/**
 * 根据官方文档测试 SERVO42C 命令
 * 
 * 测试电机地址：0xE0
 * 波特率：38400
 * 
 * 接线：
 * ESP32 GPIO16 (RX) → SERVO42C TX
 * ESP32 GPIO17 (TX) → SERVO42C RX
 * ESP32 GND         → SERVO42C GND
 */

#define SERVO_BAUDRATE 38400
#define DEBUG_BAUDRATE 115200
#define MOTOR_ADDR 0xE0

HardwareSerial ServoSerial(2);

uint8_t txBuffer[20];
uint8_t rxBuffer[20];

void setup() {
    Serial.begin(DEBUG_BAUDRATE);
    delay(1000);
    
    Serial.println("\n\n");
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  SERVO42C 官方命令测试                    ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("测试电机地址: 0xE0");
    Serial.println("波特率: 38400");
    Serial.println();
    
    // 初始化串口
    Serial.println("初始化串口...");
    ServoSerial.begin(SERVO_BAUDRATE, SERIAL_8N1, 16, 17);
    delay(500);
    Serial.println("✓ 串口初始化完成");
    Serial.println();
    
    delay(2000);
    
    // 显示菜单
    printMenu();
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        
        if (cmd.length() > 0) {
            handleCommand(cmd);
        }
    }
    
    delay(10);
}

/**
 * 处理命令
 */
void handleCommand(String cmd) {
    Serial.println();
    Serial.print("→ 执行: ");
    Serial.println(cmd);
    Serial.println("─────────────────────────────────");
    
    if (cmd == "1") {
        test_read_encoder();
    }
    else if (cmd == "2") {
        test_read_pulses();
    }
    else if (cmd == "3") {
        test_read_position();
    }
    else if (cmd == "4") {
        test_read_angle_error();
    }
    else if (cmd == "5") {
        test_read_enable_state();
    }
    else if (cmd == "6") {
        test_read_stall_state();
    }
    else if (cmd == "10") {
        test_set_work_mode();
    }
    else if (cmd == "20") {
        test_enable_motor();
    }
    else if (cmd == "21") {
        test_disable_motor();
    }
    else if (cmd == "30") {
        test_run_forward();
    }
    else if (cmd == "31") {
        test_run_reverse();
    }
    else if (cmd == "32") {
        test_stop_motor();
    }
    else if (cmd == "all") {
        runAllTests();
    }
    else if (cmd == "menu" || cmd == "help") {
        printMenu();
    }
    else {
        Serial.println("✗ 未知命令，输入 'menu' 查看菜单");
    }
    
    Serial.println();
}

/**
 * 测试1: 读取编码器值 (0x30)
 */
void test_read_encoder() {
    Serial.println("【测试1】读取编码器值 (0x30)");
    Serial.println("文档: 发送 e0 30 tCHK");
    Serial.println("返回: e0 + int32_t进位值 + uint16_t编码器值 + CHK (共8字节)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0x30;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 8)) {
        int32_t carrier = ((int32_t)rxBuffer[1] << 24) | ((int32_t)rxBuffer[2] << 16) |
                          ((int32_t)rxBuffer[3] << 8) | rxBuffer[4];
        uint16_t value = ((uint16_t)rxBuffer[5] << 8) | rxBuffer[6];
        
        float angle = (value * 360.0) / 65536.0;
        
        Serial.println("✓ 读取成功！");
        Serial.print("  进位值: ");
        Serial.println(carrier);
        Serial.print("  编码器值: ");
        Serial.print(value);
        Serial.print(" (0x");
        Serial.print(value, HEX);
        Serial.println(")");
        Serial.print("  当前角度: ");
        Serial.print(angle, 2);
        Serial.println("°");
    } else {
        Serial.println("✗ 读取失败或超时");
    }
}

/**
 * 测试2: 读取输入累计脉冲数 (0x33)
 */
void test_read_pulses() {
    Serial.println("【测试2】读取输入累计脉冲数 (0x33)");
    Serial.println("文档: 发送 e0 33 tCHK");
    Serial.println("返回: e0 + int32_t脉冲数 + CHK (共6字节)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0x33;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 6)) {
        int32_t pulses = ((int32_t)rxBuffer[1] << 24) | ((int32_t)rxBuffer[2] << 16) |
                         ((int32_t)rxBuffer[3] << 8) | rxBuffer[4];
        
        Serial.println("✓ 读取成功！");
        Serial.print("  累计脉冲数: ");
        Serial.println(pulses);
    } else {
        Serial.println("✗ 读取失败或超时");
    }
}

/**
 * 测试3: 读取闭环电机实时位置 (0x36)
 */
void test_read_position() {
    Serial.println("【测试3】读取闭环电机实时位置 (0x36)");
    Serial.println("文档: 发送 e0 36 tCHK");
    Serial.println("返回: e0 + int32_t位置 + CHK (共6字节)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0x36;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 6)) {
        int32_t position = ((int32_t)rxBuffer[1] << 24) | ((int32_t)rxBuffer[2] << 16) |
                           ((int32_t)rxBuffer[3] << 8) | rxBuffer[4];
        
        float circles = position / 65536.0;
        
        Serial.println("✓ 读取成功！");
        Serial.print("  实时位置: ");
        Serial.println(position);
        Serial.print("  转了: ");
        Serial.print(circles, 3);
        Serial.println(" 圈");
    } else {
        Serial.println("✗ 读取失败或超时");
    }
}

/**
 * 测试4: 读取位置角度误差 (0x39)
 */
void test_read_angle_error() {
    Serial.println("【测试4】读取位置角度误差 (0x39)");
    Serial.println("文档: 发送 e0 39 tCHK");
    Serial.println("返回: e0 + int16_t误差 + CHK (共4字节)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0x39;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 4)) {
        int16_t error = ((int16_t)rxBuffer[1] << 8) | rxBuffer[2];
        float errorDegree = (error * 360.0) / 65536.0;
        
        Serial.println("✓ 读取成功！");
        Serial.print("  角度误差: ");
        Serial.print(error);
        Serial.print(" (");
        Serial.print(errorDegree, 3);
        Serial.println("°)");
    } else {
        Serial.println("✗ 读取失败或超时");
    }
}

/**
 * 测试5: 读取使能状态 (0x3A)
 */
void test_read_enable_state() {
    Serial.println("【测试5】读取使能状态 (0x3A)");
    Serial.println("文档: 发送 e0 3a tCHK");
    Serial.println("返回: e0 01 CHK (已使能) 或 e0 02 CHK (未使能)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0x3A;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 3)) {
        Serial.println("✓ 读取成功！");
        Serial.print("  使能状态: ");
        if (rxBuffer[1] == 0x01) {
            Serial.println("已使能 ✓");
        } else if (rxBuffer[1] == 0x02) {
            Serial.println("未使能");
        } else {
            Serial.print("未知 (0x");
            Serial.print(rxBuffer[1], HEX);
            Serial.println(")");
        }
    } else {
        Serial.println("✗ 读取失败或超时");
    }
}

/**
 * 测试6: 读取堵转状态 (0x3E)
 */
void test_read_stall_state() {
    Serial.println("【测试6】读取堵转状态 (0x3E)");
    Serial.println("文档: 发送 e0 3e tCHK");
    Serial.println("返回: e0 01 CHK (堵转) 或 e0 02 CHK (正常)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0x3E;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    if (sendReceive(txBuffer, 3, rxBuffer, 3)) {
        Serial.println("✓ 读取成功！");
        Serial.print("  堵转状态: ");
        if (rxBuffer[1] == 0x01) {
            Serial.println("⚠ 堵转！");
        } else if (rxBuffer[1] == 0x02) {
            Serial.println("正常 ✓");
        } else {
            Serial.print("未知 (0x");
            Serial.print(rxBuffer[1], HEX);
            Serial.println(")");
        }
    } else {
        Serial.println("✗ 读取失败或超时");
    }
}

/**
 * 测试10: 设置工作模式为 CR_UART (0x82)
 */
void test_set_work_mode() {
    Serial.println("【测试10】设置工作模式为 CR_UART (0x82)");
    Serial.println("文档: 发送 e0 82 02 tCHK");
    Serial.println("00=CR_OPEN, 01=CR_vFOC, 02=CR_UART");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0x82;
    txBuffer[2] = 0x02;  // CR_UART
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    Serial.println("⚠ 注意：设置成功后需要重新上电才能生效！");
    Serial.println();
    
    if (sendReceive(txBuffer, 4, rxBuffer, 3)) {
        if (rxBuffer[1] == 0x01) {
            Serial.println("✓ 设置成功！");
            Serial.println("  请重新上电 ESP32 和电机");
        } else {
            Serial.println("✗ 设置失败");
        }
    } else {
        Serial.println("✗ 命令发送失败或超时");
    }
}

/**
 * 测试20: 使能电机 (0xF3)
 */
void test_enable_motor() {
    Serial.println("【测试20】使能电机 (0xF3)");
    Serial.println("文档: 发送 e0 f3 01 tCHK");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0xF3;
    txBuffer[2] = 0x01;  // 使能
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    bool received = sendReceive(txBuffer, 4, rxBuffer, 3);
    
    // 检查返回值
    Serial.print("返回状态: 0x");
    if (received && rxBuffer[1] != 0) {
        Serial.println(rxBuffer[1], HEX);
    } else {
        Serial.println("无");
    }
    
    if (received && rxBuffer[1] == 0x01) {
        Serial.println("✓ 使能成功！");
        Serial.println("  电机已通电锁定");
    } else if (received) {
        Serial.print("⚠ 返回值: 0x");
        Serial.print(rxBuffer[1], HEX);
        Serial.println(" (不是预期的 0x01)");
        Serial.println("  但命令可能已生效，请观察");
    } else {
        Serial.println("✗ 命令发送失败或超时");
    }
}

/**
 * 测试21: 失能电机 (0xF3)
 */
void test_disable_motor() {
    Serial.println("【测试21】失能电机 (0xF3)");
    Serial.println("文档: 发送 e0 f3 00 tCHK");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0xF3;
    txBuffer[2] = 0x00;  // 失能
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    if (sendReceive(txBuffer, 4, rxBuffer, 3)) {
        if (rxBuffer[1] == 0x01) {
            Serial.println("✓ 失能成功！");
            Serial.println("  电机已断电，可手动转动");
        } else {
            Serial.println("✗ 失能失败");
        }
    } else {
        Serial.println("✗ 命令发送失败或超时");
    }
}

/**
 * 测试30: 正向运动 (0xF6)
 */
void test_run_forward() {
    Serial.println("【测试30】正向运动 (0xF6)");
    Serial.println("文档: 发送 e0 f6 32 tCHK (速度50)");
    Serial.println("最高位=方向(0正1反), 低7位=速度(0-127)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0xF6;
    txBuffer[2] = 0x32;  // 0x32 = 50 (正向)
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    bool received = sendReceive(txBuffer, 4, rxBuffer, 3);
    
    // 检查返回值
    Serial.print("返回状态: 0x");
    if (received && rxBuffer[1] != 0) {
        Serial.println(rxBuffer[1], HEX);
    } else {
        Serial.println("无");
    }
    
    if (received && rxBuffer[1] == 0x01) {
        Serial.println("✓ 运动成功！");
        Serial.println("  电机应该正向转动");
        Serial.println("  输入 '32' 可停止");
    } else if (received) {
        Serial.print("⚠ 返回值: 0x");
        Serial.print(rxBuffer[1], HEX);
        Serial.println(" (不是预期的 0x01)");
        Serial.println("  但电机可能已经在运动，请观察");
    } else {
        Serial.println("✗ 命令发送失败或超时");
    }
}

/**
 * 测试31: 反向运动 (0xF6)
 */
void test_run_reverse() {
    Serial.println("【测试31】反向运动 (0xF6)");
    Serial.println("文档: 发送 e0 f6 b2 tCHK (速度50，反向)");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0xF6;
    txBuffer[2] = 0xB2;  // 0xB2 = 0x80 | 0x32 = 反向50
    txBuffer[3] = calculateChecksum(txBuffer, 3);
    
    bool received = sendReceive(txBuffer, 4, rxBuffer, 3);
    
    // 检查返回值
    Serial.print("返回状态: 0x");
    if (received && rxBuffer[1] != 0) {
        Serial.println(rxBuffer[1], HEX);
    } else {
        Serial.println("无");
    }
    
    if (received && rxBuffer[1] == 0x01) {
        Serial.println("✓ 运动成功！");
        Serial.println("  电机应该反向转动");
        Serial.println("  输入 '32' 可停止");
    } else if (received) {
        Serial.print("⚠ 返回值: 0x");
        Serial.print(rxBuffer[1], HEX);
        Serial.println(" (不是预期的 0x01)");
        Serial.println("  但电机可能已经在运动，请观察");
    } else {
        Serial.println("✗ 命令发送失败或超时");
    }
}

/**
 * 测试32: 停止电机 (0xF7)
 */
void test_stop_motor() {
    Serial.println("【测试32】停止电机 (0xF7)");
    Serial.println("文档: 发送 e0 f7 tCHK");
    Serial.println();
    
    txBuffer[0] = MOTOR_ADDR;
    txBuffer[1] = 0xF7;
    txBuffer[2] = calculateChecksum(txBuffer, 2);
    
    bool received = sendReceive(txBuffer, 3, rxBuffer, 3);
    
    // 检查返回值
    Serial.print("返回状态: 0x");
    if (received && rxBuffer[1] != 0) {
        Serial.println(rxBuffer[1], HEX);
    } else {
        Serial.println("无");
    }
    
    if (received && rxBuffer[1] == 0x01) {
        Serial.println("✓ 停止成功！");
        Serial.println("  电机已停止");
    } else if (received) {
        Serial.print("⚠ 返回值: 0x");
        Serial.print(rxBuffer[1], HEX);
        Serial.println(" (不是预期的 0x01)");
        Serial.println("  但电机可能已经停止，请观察");
    } else {
        Serial.println("✗ 命令发送失败或超时");
    }
}

/**
 * 运行所有测试
 */
void runAllTests() {
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  运行所有测试                             ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    
    // 读取命令测试
    Serial.println("═══ 读取命令测试 ═══");
    Serial.println();
    
    test_read_enable_state();
    delay(500);
    Serial.println();
    
    test_read_encoder();
    delay(500);
    Serial.println();
    
    test_read_pulses();
    delay(500);
    Serial.println();
    
    test_read_position();
    delay(500);
    Serial.println();
    
    test_read_angle_error();
    delay(500);
    Serial.println();
    
    test_read_stall_state();
    delay(500);
    Serial.println();
    
    // 控制命令测试
    Serial.println("═══ 控制命令测试 ═══");
    Serial.println();
    
    test_enable_motor();
    delay(1000);
    Serial.println();
    
    test_run_forward();
    delay(3000);
    Serial.println();
    
    test_stop_motor();
    delay(1000);
    Serial.println();
    
    test_disable_motor();
    Serial.println();
    
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  所有测试完成                             ║");
    Serial.println("╚═══════════════════════════════════════════╝");
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
bool sendReceive(uint8_t* tx, int txLen, uint8_t* rx, int rxLen) {
    Serial.print("发送: ");
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
            
            // 第一个字节必须是电机地址
            if (rxIndex == 0 && byte != MOTOR_ADDR) {
                continue;
            }
            
            rx[rxIndex++] = byte;
            
            // 收够了
            if (rxIndex >= rxLen) {
                // 验证校验和
                uint8_t calcChecksum = calculateChecksum(rx, rxLen - 1);
                uint8_t recvChecksum = rx[rxLen - 1];
                
                Serial.print("收到: ");
                printHex(rx, rxLen);
                
                if (calcChecksum == recvChecksum) {
                    Serial.println("  ✓ 校验成功");
                    return true;
                } else {
                    Serial.print("  ✗ 校验失败 (期望: 0x");
                    Serial.print(calcChecksum, HEX);
                    Serial.print(", 收到: 0x");
                    Serial.print(recvChecksum, HEX);
                    Serial.println(")");
                    return false;
                }
            }
        }
        delay(1);
    }
    
    if (rxIndex > 0) {
        Serial.print("收到（不完整）: ");
        printHex(rx, rxIndex);
    } else {
        Serial.println("✗ 超时，无响应");
    }
    
    return false;
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
 * 打印菜单
 */
void printMenu() {
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  测试菜单                                 ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    Serial.println("【读取命令】");
    Serial.println("  1  - 读取编码器值 (0x30)");
    Serial.println("  2  - 读取累计脉冲 (0x33)");
    Serial.println("  3  - 读取实时位置 (0x36)");
    Serial.println("  4  - 读取角度误差 (0x39)");
    Serial.println("  5  - 读取使能状态 (0x3A)");
    Serial.println("  6  - 读取堵转状态 (0x3E)");
    Serial.println();
    Serial.println("【设置命令】");
    Serial.println("  10 - 设置工作模式为 CR_UART (0x82) ⚠");
    Serial.println();
    Serial.println("【控制命令】");
    Serial.println("  20 - 使能电机 (0xF3)");
    Serial.println("  21 - 失能电机 (0xF3)");
    Serial.println("  30 - 正向运动 (0xF6)");
    Serial.println("  31 - 反向运动 (0xF6)");
    Serial.println("  32 - 停止电机 (0xF7)");
    Serial.println();
    Serial.println("【批量测试】");
    Serial.println("  all  - 运行所有测试");
    Serial.println();
    Serial.println("  menu - 显示此菜单");
    Serial.println();
    Serial.println("提示：输入数字后按回车");
    Serial.println();
}

