; ============================================================
; NCVS Inno Setup 스크립트
; 빌드: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; 사용법: ISCC.exe setup.iss
;         → Output\NCVS_Setup.exe 생성
; ============================================================

#define AppName    "NCVS"
#define AppVersion "1.0.0"
#define AppPublisher "RICS"
#define AppURL     "http://localhost:3000"
#define AppExeName "NCVS.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=NCVS_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 설치 완료 후 자동 실행 런처
SetupIconFile=
UninstallDisplayIcon={app}\{#AppExeName}
; 관리자 권한 필요 (Program Files 설치)
PrivilegesRequired=admin
; 최소 OS: Windows 10
MinVersion=10.0

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
; 바탕화면 바로가기 (기본 체크)
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"
; 시작 프로그램 등록
Name: "startup"; Description: "Windows 시작 시 자동 실행"; GroupDescription: "추가 작업:"; Flags: unchecked

[Files]
; 런처 exe
Source: "..\dist\NCVS.exe"; DestDir: "{app}"; Flags: ignoreversion

; Python 임베디드 런타임
Source: "..\dist\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; Node.js 포터블
Source: "..\dist\node\*"; DestDir: "{app}\node"; Flags: ignoreversion recursesubdirs createallsubdirs

; 백엔드 소스
Source: "..\dist\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs

; 프론트엔드 standalone 빌드
Source: "..\dist\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs

; 환경변수 파일
Source: "..\dist\.env"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Dirs]
; DB 데이터 디렉터리 (설치 시 생성)
Name: "{app}\data"

[Icons]
; 시작 메뉴
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName} 제거"; Filename: "{uninstallexe}"

; 바탕화면
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

; 시작 프로그램
Name: "{autostartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: startup

[Run]
; 설치 직후 DB 초기화 (최초 1회)
Filename: "{app}\python\python.exe"; \
  Parameters: "-m alembic upgrade head"; \
  WorkingDir: "{app}\backend"; \
  StatusMsg: "데이터베이스 초기화 중..."; \
  Flags: runhidden waituntilterminated

; seed: admin 계정 생성
Filename: "{app}\python\python.exe"; \
  Parameters: "-m app.cli.seed"; \
  WorkingDir: "{app}\backend"; \
  StatusMsg: "관리자 계정 생성 중..."; \
  Flags: runhidden waituntilterminated

; 설치 완료 후 NCVS 실행 여부 (체크박스)
Filename: "{app}\{#AppExeName}"; \
  Description: "NCVS 지금 실행"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; 제거 전 서버 프로세스 종료
Filename: "taskkill.exe"; Parameters: "/F /IM NCVS.exe /T"; Flags: runhidden
Filename: "taskkill.exe"; Parameters: "/F /IM node.exe /T"; Flags: runhidden

[Code]
// 설치 전 기존 프로세스 종료 확인
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    Exec('taskkill.exe', '/F /IM NCVS.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
