# BACS Control

---

## 목차

1. [Server ↔ BACS 제어](#1-server--bacs-제어)
   - 1.1. [Message 구조](#11-message-구조)
   - 1.2. [UDP 제어](#12-udp-제어)
     - 1.2.1. [연결 정보 제어(Heartbeat)](#121-연결-정보-제어heartbeat)
   - 1.3. [TCP 제어](#13-tcp-제어)
     - 1.3.1. [접속 Level (Server → BACS)](#131-접속-level-server--bacs)
     - 1.3.2. [Start Up Report (BACS → Server)](#132-start-up-report-bacs--server)
     - 1.3.3. [호출 시험 명령 (Server → BACS)](#133-호출-시험-명령-server--bacs)
     - 1.3.4. [호출 시험 응답 (BACS → Server)](#134-호출-시험-응답-bacs--server)
     - 1.3.5. [오류 정보 (BACS → Server)](#135-오류-정보-bacs--server)

---

## 1. Server ↔ BACS 제어

### 1.1. Message 구조

다음의 [그림 1]는 BACS 제어 Message 의 전체적인 구조이다.

```
┌─────────────────────────────────────────────────────────────────┐
│                Message Header          Control Message           │
│  ┌──────────┬─────────────────┬──────────────────────────────┐  │
│  │ Type(2)  │ Data Length(2)  │           Data(N)            │  │
│  └──────────┴─────────────────┴──────────────────────────────┘  │
│                                                                   │
│  ┌───────────┬──────────┬──────────────┬──────────────────────┐  │
│  │ Node ID(2)│ Message  │ Message Data │   Message Data(n)    │  │
│  │           │ Type(1)  │  Length(2)   │                      │  │
│  └───────────┴──────────┴──────────────┴──────────────────────┘  │
│        Control Message Header              Control Message Data   │
└─────────────────────────────────────────────────────────────────┘
```

**그림 1 Message Format**

- **Type(2)** : 상위 1 Byte Message Direction + 하위 1 Byte Data Type
- **Data Length(2)** : Data의 크기
- **Node ID(2)** : 0~63의 값이며 0은 Master, 1~63은 Slave.
- **Message Type(1)** : Control Message 구분.
- **Message Data Length(2)** : Message Data의 길이.
- **Message Data(n)** : 각 Message Type별 Data.

#### Data Struct

```c
/* direction */
#define TCP_SE_MA   0x1000  /* server --> master */
#define TCP_SE_SL   0x2000  /* server --> slave */
#define TCP_SE_PH   0x4000  /* server --> phone */
#define TCP_MA_SE   0x0100  /* master --> server */
#define TCP_SL_SE   0x0200  /* slave --> server */
#define TCP_PH_SE   0x0400  /* phone --> server */
#define TCP_DIRECTION_MASK 0xff00

/* data type */
#define TCP_CNTL_DATA    0x0001  /* req, ack, alarm, sensor */
#define TCP_SERIAL_DATA  0x0002  /* rs232 data */
#define TCP_DATA_TYPE_MASK  0x00ff

#define TCP_MSG_MAX  1024

typedef struct _tcp_msg {
    unsigned short type;
    unsigned short msg_len;
    unsigned char msg[TCP_MSG_MAX];
} __attribute__ ((packed)) tcp_msg_t;

struct __Control_MSG_Header {
    unsigned short node_id;
    unsigned char msg_type;
    unsigned short msg_len;
} __attribute__ ((packed));
```

#### Message Structure

| Field | | | Length | Description |
|---|---|---|---|---|
| Header | Type | | 2 Byte | Direction & Data Type |
| | Length | | 2 Byte | Control Length(5~1024) |
| Control Message | Control Message Header | Node ID | 2 Byte | Destination ID(0 ~ 63) |
| | | Type | 1 Byte | Control Message Type |
| | | Length | 2 Byte | Control Message Data Length(n) |
| | Control Message Data | | n Byte | Control Data |

---

### 1.2. UDP 제어

BACS 에서 사용하는 UDP port 는 **7788** 이다.

```
제어 서버                                    RICS-M
   │                                            │
   │ ──────── SE_MA_Connect_REQ ──────────────► │
   │                                            │
   │ ◄──────── SE_MA_Connect_RPT ───────────── │
   │                                            │
```

**그림 2 BACS UDP 제어**

---

### 1.2.1. 연결 정보 제어(Heartbeat)

UDP 를 통한 연결 정보 확인 메시지로 BACS 의 상태 정보를 제어 서버에서 요청할 때마다 report 한다. 서버에서 주기적으로 BACS 장비의 연결 상태를 확인한다.

#### Data Struct

```c
typedef struct {
    struct __Control_MSG_Header header;
} SE_MA_Connection_REQ_t;

typedef struct {
    struct __Control_MSG_Header header;
    struct {
        unsigned long long alive;
    } __attribute__ ((packed)) data;
} MA_SE_Connection_RPT_t;
```

#### SE_MA_Connect_REQ

| Field | | Length | Name | Value | Transmit Ordering |
|---|---|---|---|---|---|
| Header | Type | 2 Byte | Type | 0x1001 | 01 10 |
| | Length | 2 Byte | Length | 5 | 05 00 |
| Control Message | Node ID | 2 Byte | Destination ID | 0 | 00 00 |
| | Message Type | 1 Byte | CONNECT_ACK | 0x12 | |
| | Message Length | 2 Byte | Length | 0 | 00 00 |
| | Message Data | | | | |

#### MA_SE_Connect_RPT

| Field | | Length | Name | Value | Transmit Ordering |
|---|---|---|---|---|---|
| Header | Type | 2 Byte | Type | 0x0101 | 01 01 |
| | Length | 2 Byte | Length | 13 | 0D 00 |
| Control Message | Node ID | 2 Byte | Source ID | 0 | 00 00 |
| | Message Type | 1 Byte | CONNECT_RPT | 0x92 | |
| | Message Length | 2 Byte | Length | 8 | 08 00 |
| | Message Data | 8 Byte | Connection State | 64 Bit data : 1 on, 0 off | LSB … MSB |

| Name | Bit | Description |
|---|---|---|
| Connection State | [63:0] | BACS 기능 동작시 데이터는 무시 |

---

### 1.3. TCP 제어

BACS 는 server socket 을 사용하며 TCP port 는 **7788** 을 사용한다.

```
제어 서버                                        BACS
   │                                               │
   │ ──────────────── TCP connect ───────────────► │
   │                                               │  5초 이내에
Accept 이후                                        │  수신이 안되면
5초 이내                                           │  TCP Close
전송  │ ◄──────────────── Accept ─────────────────│
   │                                               │
   │ ◄── SE_MA_Connect_Level_RPT ─────────────── │
   │      01 10 09 00 00 00 66 04 00              │  연결 거부 조건인
   │                                               │  경우
   │ ──── MA_SE_Error_RPT(code 302) ────────────► │
   │      & TCP Close                              │
   │      01 01 ?? ?? 00 00 91 ?? ??              │
   │                                               │
   │ ◄── MA_SE_Start_Up_RPT ─────────────────── │
   │      01 01 05 00 00 00 90 00                 │
   │                                               │
   │ ──────────── TCP 제어 요청 ────────────────► │
   │                                               │
   │ ◄─────────── 제어 결과 응답 ───────────────  │
   │                                               │
   │ ──────────── TCP Close ─────────────────────► │
   ▼                                               ▼
```

**그림 3 BACS TCP 제어**

BACS 장치는 TCP Session 연결 후 제어 요청이 없는 경우 약 60 초간 TCP Session 을 유지하며, 제어 요청이 있을 경우 Timeout 시간은 초기화 된다.

a. Server에서 BACS로 TCP 연결요청
b. BACS에서 Accept
c. Server에서 BACS로 SE_MA_Connect_Level_RPT 전송
d. BACS에서 판단 후 MA_SE_Start_Up_RPT 전송 또는 MA_SE_Error_RPT 전송 후 연결 종료
e. Server에서 MA_SE_Start_Up_RPT 수신 후 BACS 제어
f. 제어 완료 후 TCP 연결 종료

---

### 1.3.1. 접속 Level (Server → BACS)

제어를 위한 TCP session 이 이미 연결되어 있는 경우 기존 연결을 유지하고, 새로운 연결은 Error code 302 를 report 하고 disconnect 한다.

#### Data Struct

```c
typedef struct {
    struct __Control_MSG_Header header;
    struct {
        unsigned int level;
    } __attribute__ ((packed)) data;
} SE_MA_Connect_Level_REQ_t;
```

#### SE_MA_Connect_Level_REQ

| Field | | Length | Desc. | Value | Transmit Ordering |
|---|---|---|---|---|---|
| Header | Type | 2 Byte | Type | 0x1001 | 01 10 |
| | Length | 2 Byte | Length | 9 | 09 00 |
| Control Message | Node ID | 2 Byte | Destination ID | 0 | 00 00 |
| | Message Type | 1 Byte | CONNECT_LEVEL_RPT | 0x66 | 66 |
| | Message Length | 2 Byte | Length | 4 | 04 00 |
| | Message Data | 4 Byte | Level | 0x0000e7e7 | e7 e7 00 00 |

---

### 1.3.2. Start Up Report (BACS → Server)

TCP session 이 연결된 후 접속 Level 이 확인 되어 제어권이 주어지면, 1 회 전송되는 메시지이다.

#### Data Struct

```c
typedef struct {
    struct __Control_MSG_Header header;
} MA_SE_Start_Up_RPT_t;
```

#### MA_SE_Start_Up_RPT

| Field | | Length | Desc. | Value | Transmit Ordering |
|---|---|---|---|---|---|
| Header | Type | 2 Byte | Type | 0x0101 | 01 01 |
| | Length | 2 Byte | Length | 5 | 05 00 |
| Control Message | Node ID | 2 Byte | Source ID | 0 | 00 00 |
| | Message Type | 1 Byte | START_UP_RPT | 0x90 | 90 |
| | Message Length | 2 Byte | Length | 0 | 00 |
| | Message Data | | | | |

---

### 1.3.3. 호출 시험 명령 (Server → BACS)

TCP session 이 연결된 이후 제어서버(Server)의 요청이 있을 때 전송된다.

BACS 로 호출 시험 명령을 보낸다. BACS 의 port 와 phone number length 그리고 phone number 를 Message Data 로 전송한다.

Phone number length 는 0~16 이며, Phone number 가 16 미만이면 나머지는 0(chunk)으로 채운다.

#### Data Struct

```c
typedef struct {
    struct __Control_MSG_Header header;
    struct {
        unsigned char Port;
        unsigned char Phone_length;
        unsigned char Phone_Num[16];
    } __attribute__ ((packed)) data;
} SE_MA_CALL_REQ_t;
```

#### SE_MA_CALL_REQ

| Field | | Length | Name | Value | Transmit Ordering |
|---|---|---|---|---|---|
| Header | Type | 2 Byte | Type | 0x1001 | 01 10 |
| | Length | 2 Byte | Length | 23 | 17 00 |
| Control Message | Node ID | 2 Byte | Destination ID | 1 | 01 00 |
| | Message Type | 1 Byte | CALL_ACK | 0x50 | 50 |
| | Message Length | 2 Byte | Length | 18 | 12 00 |
| | Message Data | 18 Byte | Port | 0~3 | |
| | | | Phone length | 0~16 | |
| | | | Phone Number | Number + chunk | |

---

### 1.3.4. 호출 시험 응답 (BACS → Server)

호출 시험이 완료 된 후 BACS 에서 Server 로 전송되는 응답 데이터이다.

#### Data Struct

```c
typedef struct {
    struct __Control_MSG_Header header;
    struct {
        unsigned int level;
    } __attribute__ ((packed)) data;
} MA_SE_CALL_RPT_t;
```

#### MA_SE_CALL_RPT

| Field | | Length | Name | Value | Transmit Ordering |
|---|---|---|---|---|---|
| Header | Type | 2 Byte | Type | 0x0201 | 01 02 |
| | Length | 2 Byte | Length | 7 | 07 00 |
| Control Message | Node ID | 2 Byte | Source ID | 1 | 01 00 |
| | Message Type | 1 Byte | CALL_RPT | 0xd0 | |
| | Message Length | 2 Byte | Length | 2 | 02 00 |
| | Message Data | 2 Byte | Result | OK : 0x0011 | |
| | | | | NK : 0x0013 or 0x0016 | |
| | | | | BUSY : 0x0015 | |
| | | | | FAIL : 0x0023 | |

- **OK** : 호출이 성공으로 끝남.
- **NK** : 발신 성공 후 DTMF 일부 소실
- **BUSY** : No idle 중복 요청
- **FAIL** : DTMF 완전 소실

호출 명령 후 OK 응답까지 30 초 정도 소요.
호출 명령 후 실패 응답까지 50 초 정도 소요.

---

### 1.3.5. 오류 정보 (BACS → Server)

Error Report 의 다음의 2 가지 경우에 사용된다.

a. 새로운 User가 제어권을 가져간 경우
b. 새로운 User가 제어권을 가져오지 못한 경우

새로운 user 가 제어권을 가져간 경우 기존 user 에게 error code 300 을 전송하고, 새로운 user 에게 error code 301 을 전송한다.

새로운 user 의 제어권 획득이 거부된 경우 새로운 user 에게 error code 302 를 전송한다.

#### Data Struct

```c
#define ERROR_RPT_ERR_MSG_MAX  64

typedef struct {
    struct __Control_MSG_Header header;
    struct {
        unsigned short err_code;
        unsigned char err_msg[ERROR_RPT_ERR_MSG_MAX];
    } __attribute__ ((packed)) data;
} MA_SE_Error_RPT_t;
```

#### MA_SE_Error_RPT

| Field | | Length | Desc. | Value | Transmit Ordering |
|---|---|---|---|---|---|
| Header | Type | 2 Byte | Type | Node ID 0 : 0x0101 | 01 01 |
| | | | | Node ID 1~63 : 0x0201 | 01 02 |
| | Length | 2 Byte | Length | 7 + n | |
| Control Message | Node ID | 2 Byte | Source ID | 0 ~ 63 | (00~3F) 00 |
| | Message Type | 1 Byte | ERROR_RPT | 0x91 | |
| | Message Length | 2 Byte | Length | 2 ~ 2+n | (02 00) ~ (xx xx) |
| | Message Data | 2 Byte | Error Code | 300~302 | 2C 01 ~ 2E 01 |
| | | n Byte | Error Message(Max 64) | String | |

#### Error Code

| Code | Message | Description |
|---|---|---|
| 100 (0x64) | Command/Serial | Session Idle Timeout |
| 200 (0xC8) | Ex) "Ctrl Type Error!!" | Message Error |
| 300 (0x12C) | Ex) "123.123.123.123" | Lost Control, Report New Connected IP |
| 301 (0x12D) | Ex) "123.123.123.123" | Intercept Control, Report Old Connected IP |
| 302 (0x12E) | Ex) "123.123.123.123" | Already Control, Report Current Connected IP |

---

## 2. 로컬 네트워크 현장 테스트 가이드

> 인터넷을 끊고 BACS 로컬 네트워크에 접속했을 때 처음부터 끝까지 따라하는 절차입니다.

---

### STEP 1. 노트북 IP 설정

로컬 네트워크 대역에 맞게 노트북 IP를 수동으로 변경합니다.

**macOS 기준:**
1. 시스템 환경설정 → 네트워크 → 사용 중인 어댑터 선택
2. IPv4 구성: 수동
3. IP 주소: 로컬 네트워크 대역에 맞는 주소 입력 (예: 192.168.1.100)
4. 서브넷 마스크: 255.255.255.0
5. 적용 후 저장

---

### STEP 2. 네트워크 연결 확인

터미널에서 아래 명령어로 BACS 장비까지 통신 가능한지 먼저 확인합니다.

    # 노트북 현재 IP 확인
    ifconfig | grep "inet "

    # AGW 장비 통신 확인
    ping -c 3 192.168.1.10

    # IPSEC 장비 통신 확인
    ping -c 3 192.168.2.10

- ping 응답이 오면 → STEP 3 진행
- ping 응답이 없으면 → IP 설정 재확인 후 네트워크 담당자에게 문의

---

### STEP 3. 패킷 캡처 준비 (별도 터미널)

실제 UDP 송수신 내용을 기록하기 위해 터미널을 하나 더 열고 아래 명령어를 실행해 둡니다.

    # UDP 7788 포트 패킷 캡처 (main.py 실행 전에 미리 시작)
    sudo tcpdump -i any udp port 7788 -XX

비밀번호 입력 후 대기 상태로 두고 STEP 4 진행.

---

### STEP 4. 실제 장비 헬스체크 실행

    cd /Users/kjw/Documents/NCVS_project/ncvs_udp_test
    python3 main.py

정상 출력 예시:

    [BACS 헬스체크] 장비 목록 로딩: devices.json
      → 2대 장비 등록 확인
      → UDP 헬스체크 시작 (병렬, 포트 7788, 타임아웃 5초)
    ==================================================
    장비명               IP               타입     상태       지연(ms)
    --------------------------------------------------
    BACS-AGW-001        192.168.1.10     AGW      ONLINE    12.3
    BACS-IPSEC-001      192.168.2.10     IPSEC    ONLINE    8.7
    ==================================================
    총 2대 | ONLINE: 2대 | OFFLINE: 0대

---

### STEP 5. 통합 테스트 실행

    python3 -m pytest -m integration -v -s 2>&1

정상 출력 예시:

    test_checker.py::TestCheckIntegration::test_check_real_device_agw PASSED
    test_checker.py::TestCheckIntegration::test_check_real_device_ipsec PASSED
    2 passed

---

### STEP 6. 결과 판단

| 결과 | 의미 | 조치 |
|---|---|---|
| 전 단계 정상 | 개발 완료, 실 운용 가능 | 완료 |
| ping은 되는데 OFFLINE | UDP 패킷 송수신 문제 | STEP 7 진행 |
| ping 자체가 안 됨 | 네트워크 연결 문제 | IP 설정 재확인 |
| 응답은 오는데 OFFLINE | 응답 패킷 형식 불일치 | STEP 7 진행 |

---

### STEP 7. 문제 발생 시 - 인터넷 복구 후 Copilot에게 전달할 자료

인터넷에 다시 연결한 뒤 아래 자료를 Copilot에게 전달하면 디아그노즈(스킬 4)를 즉시 진행합니다.

#### 수집 명령어 (현장에서 실행 후 바탕화면에 저장)

    {
      echo "=== ifconfig ==="
      ifconfig | grep "inet "
      echo ""
      echo "=== ping AGW ==="
      ping -c 3 192.168.1.10
      echo ""
      echo "=== ping IPSEC ==="
      ping -c 3 192.168.2.10
      echo ""
      echo "=== main.py ==="
      python3 main.py
      echo ""
      echo "=== integration test ==="
      python3 -m pytest -m integration -v -s
    } 2>&1 | tee ~/Desktop/bacs_result.txt

실행 후 ~/Desktop/bacs_result.txt 파일을 인터넷 복구 후 Copilot에 전달.
tcpdump 는 별도 터미널에서 실행, Ctrl+C 로 중단 후 출력 내용 복사.

#### 말로 알려줄 사항

| 항목 | 확인 내용 |
|---|---|
| 장비 실제 IP | devices.json 의 IP와 실제 장비 IP가 일치하는지 |
| 포트 번호 | 7788 이 맞는지 현장 담당자 확인 |
| tcpdump 패킷 방향 | 패킷이 나가기만 하는지 / 응답도 오는지 |
| 응답 패킷 hex 값 | 응답이 오는 경우 실제 바이트 값 (예: 01 01 0D ...) |

#### Copilot 전달 문구 템플릿

    로컬 네트워크 테스트 결과 문제 발생.
    디아그노즈 스킬로 분석해줘.

    [bacs_result.txt 내용]
    (파일 전체 붙여넣기)

    [tcpdump 결과]
    (캡처 내용 붙여넣기)

    [추가 사항]
    - 실제 장비 IP: xxx.xxx.xxx.xxx
    - 포트: 7788 맞음 / 틀림 (실제 포트: xxxx)
    - tcpdump: 패킷 나가기만 함 / 응답도 옴
