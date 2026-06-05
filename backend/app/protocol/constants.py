# UDP 패킷 타입 식별자 (little-endian uint16)
TYPE_SE_MA_CNTL = 0x1001  # SE → MA 제어 패킷 (요청)
TYPE_MA_SE_CNTL = 0x0101  # MA → SE 제어 패킷 (응답)

# 커맨드 바이트
MSG_CONNECT_RPT = 0x92   # MA_SE_Connect_RPT 커맨드
