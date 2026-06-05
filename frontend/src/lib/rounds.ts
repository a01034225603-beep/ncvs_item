/**
 * 엣지 컬러링 기반 라운드 계산 유틸리티
 *
 * 실제 BACS 장비 제약:
 *   - 한 장비는 어느 순간에나 단 하나의 페어에만 참여 가능 (발신/수신 역할 무관)
 *   - 발신 중에는 수신 불가, 수신 중에는 발신 불가
 *
 * 따라서 같은 라운드 안에서 한 장비는 어떤 역할로도 두 번 등장할 수 없다.
 * 이 제약이 백엔드 DeviceLocker 의 동작과 정확히 일치한다.
 *
 * tests/page.tsx 의 시나리오 빌더와 call-test/page.tsx 의 진행 화면
 * 양쪽에서 공통으로 사용한다.
 */

export interface Pair {
  /** 프론트 전용 고유 키 (백엔드 pair_id 또는 임시 로컬 ID) */
  id: string;
  /** 발신 장비 ID */
  s: number;
  /** 착신 장비 ID */
  r: number;
}

export interface Round {
  pairs: Pair[];
}

/**
 * Pair 배열을 받아 라운드별로 그룹핑한다.
 *
 * 같은 라운드에 속한 페어는 서로 장비가 전혀 겹치지 않아
 * 백엔드 DeviceLocker 가 모두 동시에(병렬로) 실행할 수 있다.
 *
 * 핵심 제약: 장비 하나가 발신/수신 역할 무관하게 한 라운드에 1번만 등장.
 * usedDevices 단일 집합으로 발신자·수신자를 함께 추적한다.
 */
export function computeRounds(pairs: Pair[]): Round[] {
  // 각 라운드의 사용 중인 장비 집합 (발신/수신 역할 구분 없이 통합 관리)
  const rounds: { usedDevices: Set<number>; pairs: Pair[] }[] = [];

  for (const pair of pairs) {
    let placed = false;
    for (const round of rounds) {
      // 발신 장비(s)와 착신 장비(r) 모두 이 라운드에서 미사용이어야 배치 가능
      if (!round.usedDevices.has(pair.s) && !round.usedDevices.has(pair.r)) {
        round.usedDevices.add(pair.s);
        round.usedDevices.add(pair.r);
        round.pairs.push(pair);
        placed = true;
        break;
      }
    }
    if (!placed) {
      // 기존 라운드에 배치 불가 → 새 라운드 생성
      rounds.push({
        usedDevices: new Set([pair.s, pair.r]),
        pairs: [pair],
      });
    }
  }

  return rounds.map((r) => ({ pairs: r.pairs }));
}

/** 라운드 인덱스 → 강조 색상 (순환) */
export const ROUND_COLORS = [
  "#5d9b94", "#e0a96d", "#8b8fce", "#c97b84",
  "#6bbc7a", "#d4ae5c", "#7ab8de", "#b07ac9",
];
