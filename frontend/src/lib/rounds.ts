/**
 * Vizing 엣지 컬러링 기반 라운드 계산 유틸리티
 *
 * 같은 라운드에서 각 노드는 송신자(sender) 1번 + 수신자(receiver) 1번만 허용.
 * 즉, 한 라운드 안의 페어들은 장비 충돌 없이 모두 병렬 실행 가능하다.
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
 * 같은 라운드에 속한 페어는 서로 발신자·수신자가 겹치지 않아
 * 스케줄러가 동시에(병렬로) 실행할 수 있다.
 */
export function computeRounds(pairs: Pair[]): Round[] {
  const rounds: { senders: Set<number>; receivers: Set<number>; pairs: Pair[] }[] = [];

  for (const pair of pairs) {
    let placed = false;
    for (const round of rounds) {
      if (!round.senders.has(pair.s) && !round.receivers.has(pair.r)) {
        round.senders.add(pair.s);
        round.receivers.add(pair.r);
        round.pairs.push(pair);
        placed = true;
        break;
      }
    }
    if (!placed) {
      rounds.push({
        senders: new Set([pair.s]),
        receivers: new Set([pair.r]),
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
