/** 폐쇄망 내장 한국 행정구역 좌표 데이터
 *  geo_x / geo_y: SVG 지도 기준 백분율 좌표 (0~100)
 *  좌표계: x → 서(0)에서 동(100), y → 북(0)에서 남(100)
 */

export interface DistrictCoord {
  geo_x: number;
  geo_y: number;
}

export interface SidoData {
  center: DistrictCoord;
  sigungu: Record<string, DistrictCoord>;
}

export const SIDO_LIST: string[] = [
  "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
  "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
  "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
  "경상남도", "제주특별자치도",
];

export const DISTRICTS: Record<string, SidoData> = {
  "서울특별시": {
    center: { geo_x: 39.6, geo_y: 18.3 },
    sigungu: {
      "종로구":   { geo_x: 39.1, geo_y: 17.5 }, "중구":      { geo_x: 39.5, geo_y: 18.0 },
      "용산구":   { geo_x: 39.8, geo_y: 18.6 }, "성동구":    { geo_x: 40.7, geo_y: 18.4 },
      "광진구":   { geo_x: 41.6, geo_y: 18.9 }, "동대문구":  { geo_x: 40.8, geo_y: 18.1 },
      "중랑구":   { geo_x: 41.9, geo_y: 17.6 }, "성북구":    { geo_x: 40.3, geo_y: 17.9 },
      "강북구":   { geo_x: 40.5, geo_y: 16.9 }, "도봉구":    { geo_x: 41.0, geo_y: 16.4 },
      "노원구":   { geo_x: 41.1, geo_y: 16.7 }, "은평구":    { geo_x: 38.6, geo_y: 17.6 },
      "서대문구": { geo_x: 38.8, geo_y: 18.1 }, "마포구":    { geo_x: 38.2, geo_y: 18.5 },
      "양천구":   { geo_x: 37.1, geo_y: 19.2 }, "강서구":    { geo_x: 36.4, geo_y: 18.6 },
      "구로구":   { geo_x: 37.8, geo_y: 19.7 }, "금천구":    { geo_x: 37.9, geo_y: 20.4 },
      "영등포구": { geo_x: 37.9, geo_y: 19.0 }, "동작구":    { geo_x: 38.8, geo_y: 19.3 },
      "관악구":   { geo_x: 39.0, geo_y: 19.9 }, "서초구":    { geo_x: 40.7, geo_y: 19.8 },
      "강남구":   { geo_x: 41.0, geo_y: 19.2 }, "송파구":    { geo_x: 42.1, geo_y: 19.2 },
      "강동구":   { geo_x: 42.5, geo_y: 19.0 },
    },
  },
  "부산광역시": {
    center: { geo_x: 81.5, geo_y: 61.0 },
    sigungu: {
      "중구":    { geo_x: 80.7, geo_y: 62.4 }, "서구":    { geo_x: 80.3, geo_y: 62.5 },
      "동구":    { geo_x: 80.9, geo_y: 62.3 }, "영도구":  { geo_x: 81.4, geo_y: 62.7 },
      "부산진구":{ geo_x: 81.1, geo_y: 61.4 }, "동래구":  { geo_x: 81.7, geo_y: 60.6 },
      "남구":    { geo_x: 81.6, geo_y: 62.0 }, "북구":    { geo_x: 79.9, geo_y: 60.8 },
      "해운대구":{ geo_x: 83.2, geo_y: 61.4 }, "사하구":  { geo_x: 79.6, geo_y: 62.5 },
      "금정구":  { geo_x: 81.9, geo_y: 59.9 }, "강서구":  { geo_x: 76.6, geo_y: 60.2 },
      "연제구":  { geo_x: 81.6, geo_y: 61.3 }, "수영구":  { geo_x: 82.3, geo_y: 61.9 },
      "사상구":  { geo_x: 79.7, geo_y: 61.8 }, "기장군":  { geo_x: 84.4, geo_y: 59.9 },
    },
  },
  "대구광역시": {
    center: { geo_x: 72.0, geo_y: 48.4 },
    sigungu: {
      "중구":  { geo_x: 72.0, geo_y: 48.4 }, "동구":  { geo_x: 72.7, geo_y: 48.1 },
      "서구":  { geo_x: 71.2, geo_y: 48.4 }, "남구":  { geo_x: 71.9, geo_y: 48.8 },
      "북구":  { geo_x: 71.6, geo_y: 48.1 }, "수성구":{ geo_x: 72.6, geo_y: 48.6 },
      "달서구":{ geo_x: 70.6, geo_y: 48.6 }, "달성군":{ geo_x: 68.6, geo_y: 50.1 },
    },
  },
  "인천광역시": {
    center: { geo_x: 34.1, geo_y: 20.4 },
    sigungu: {
      "중구":    { geo_x: 33.0, geo_y: 21.0 }, "동구":    { geo_x: 33.6, geo_y: 20.6 },
      "미추홀구":{ geo_x: 34.0, geo_y: 21.0 }, "연수구":  { geo_x: 34.5, geo_y: 21.5 },
      "남동구":  { geo_x: 35.0, geo_y: 21.0 }, "부평구":  { geo_x: 34.6, geo_y: 20.3 },
      "계양구":  { geo_x: 35.2, geo_y: 19.8 }, "서구":    { geo_x: 33.8, geo_y: 19.8 },
      "강화군":  { geo_x: 29.8, geo_y: 18.6 }, "옹진군":  { geo_x: 30.0, geo_y: 24.0 },
    },
  },
  "광주광역시": {
    center: { geo_x: 37.0, geo_y: 61.1 },
    sigungu: {
      "동구":  { geo_x: 37.3, geo_y: 61.0 }, "서구":  { geo_x: 36.7, geo_y: 61.0 },
      "남구":  { geo_x: 37.0, geo_y: 61.5 }, "북구":  { geo_x: 37.1, geo_y: 60.3 },
      "광산구":{ geo_x: 36.2, geo_y: 60.6 },
    },
  },
  "대전광역시": {
    center: { geo_x: 47.7, geo_y: 40.2 },
    sigungu: {
      "동구":  { geo_x: 48.4, geo_y: 40.0 }, "중구":  { geo_x: 47.5, geo_y: 40.5 },
      "서구":  { geo_x: 47.0, geo_y: 40.2 }, "유성구":{ geo_x: 47.0, geo_y: 39.5 },
      "대덕구":{ geo_x: 48.2, geo_y: 39.6 },
    },
  },
  "울산광역시": {
    center: { geo_x: 86.3, geo_y: 55.7 },
    sigungu: {
      "중구":  { geo_x: 86.0, geo_y: 55.5 }, "남구":  { geo_x: 86.3, geo_y: 56.2 },
      "동구":  { geo_x: 87.0, geo_y: 55.6 }, "북구":  { geo_x: 86.2, geo_y: 54.8 },
      "울주군":{ geo_x: 85.0, geo_y: 57.0 },
    },
  },
  "세종특별자치시": {
    center: { geo_x: 45.8, geo_y: 37.9 },
    sigungu: { "세종시": { geo_x: 45.8, geo_y: 37.9 } },
  },
  "경기도": {
    center: { geo_x: 40.0, geo_y: 22.0 },
    sigungu: {
      "수원시":  { geo_x: 40.0, geo_y: 22.5 }, "성남시":  { geo_x: 41.2, geo_y: 21.5 },
      "의정부시":{ geo_x: 40.8, geo_y: 16.8 }, "안양시":  { geo_x: 39.3, geo_y: 22.0 },
      "부천시":  { geo_x: 37.4, geo_y: 20.8 }, "광명시":  { geo_x: 37.9, geo_y: 21.5 },
      "평택시":  { geo_x: 39.5, geo_y: 26.8 }, "동두천시":{ geo_x: 40.2, geo_y: 14.5 },
      "안산시":  { geo_x: 37.4, geo_y: 23.0 }, "고양시":  { geo_x: 38.5, geo_y: 17.5 },
      "과천시":  { geo_x: 39.7, geo_y: 21.7 }, "구리시":  { geo_x: 41.4, geo_y: 18.7 },
      "남양주시":{ geo_x: 42.3, geo_y: 17.8 }, "오산시":  { geo_x: 39.5, geo_y: 24.7 },
      "시흥시":  { geo_x: 37.0, geo_y: 22.5 }, "군포시":  { geo_x: 38.8, geo_y: 22.6 },
      "의왕시":  { geo_x: 39.1, geo_y: 22.8 }, "하남시":  { geo_x: 42.2, geo_y: 20.0 },
      "용인시":  { geo_x: 41.5, geo_y: 23.3 }, "파주시":  { geo_x: 37.5, geo_y: 16.0 },
      "이천시":  { geo_x: 43.0, geo_y: 24.5 }, "안성시":  { geo_x: 41.3, geo_y: 26.5 },
      "김포시":  { geo_x: 35.9, geo_y: 18.5 }, "화성시":  { geo_x: 38.0, geo_y: 25.0 },
      "광주시":  { geo_x: 42.2, geo_y: 22.0 }, "양주시":  { geo_x: 40.3, geo_y: 15.5 },
      "포천시":  { geo_x: 41.5, geo_y: 13.5 }, "여주시":  { geo_x: 44.2, geo_y: 23.2 },
      "연천군":  { geo_x: 39.8, geo_y: 12.5 }, "가평군":  { geo_x: 43.5, geo_y: 16.0 },
      "양평군":  { geo_x: 44.0, geo_y: 20.5 },
    },
  },
  "강원특별자치도": {
    center: { geo_x: 62.3, geo_y: 18.9 },
    sigungu: {
      "춘천시":  { geo_x: 53.0, geo_y: 17.0 }, "원주시":  { geo_x: 51.5, geo_y: 23.5 },
      "강릉시":  { geo_x: 69.5, geo_y: 18.5 }, "동해시":  { geo_x: 71.0, geo_y: 23.0 },
      "태백시":  { geo_x: 68.5, geo_y: 28.5 }, "속초시":  { geo_x: 68.0, geo_y: 12.0 },
      "삼척시":  { geo_x: 71.8, geo_y: 27.5 }, "홍천군":  { geo_x: 56.5, geo_y: 18.5 },
      "횡성군":  { geo_x: 54.0, geo_y: 21.5 }, "영월군":  { geo_x: 61.0, geo_y: 28.0 },
      "평창군":  { geo_x: 60.5, geo_y: 23.0 }, "정선군":  { geo_x: 64.0, geo_y: 25.5 },
      "철원군":  { geo_x: 50.0, geo_y: 11.5 }, "화천군":  { geo_x: 53.5, geo_y: 12.5 },
      "양구군":  { geo_x: 58.0, geo_y: 12.5 }, "인제군":  { geo_x: 61.5, geo_y: 13.0 },
      "고성군":  { geo_x: 66.5, geo_y:  9.5 }, "양양군":  { geo_x: 68.0, geo_y: 15.5 },
    },
  },
  "충청북도": {
    center: { geo_x: 55.5, geo_y: 31.4 },
    sigungu: {
      "청주시":  { geo_x: 51.5, geo_y: 33.5 }, "충주시":  { geo_x: 55.0, geo_y: 28.5 },
      "제천시":  { geo_x: 59.0, geo_y: 27.0 }, "보은군":  { geo_x: 53.5, geo_y: 37.5 },
      "옥천군":  { geo_x: 51.5, geo_y: 39.0 }, "영동군":  { geo_x: 52.5, geo_y: 41.5 },
      "증평군":  { geo_x: 51.0, geo_y: 32.0 }, "진천군":  { geo_x: 49.5, geo_y: 31.0 },
      "괴산군":  { geo_x: 54.5, geo_y: 32.5 }, "음성군":  { geo_x: 50.5, geo_y: 28.5 },
      "단양군":  { geo_x: 60.5, geo_y: 25.5 },
    },
  },
  "충청남도": {
    center: { geo_x: 37.0, geo_y: 37.5 },
    sigungu: {
      "천안시":  { geo_x: 44.5, geo_y: 30.5 }, "공주시":  { geo_x: 44.0, geo_y: 36.5 },
      "보령시":  { geo_x: 36.5, geo_y: 41.0 }, "아산시":  { geo_x: 42.5, geo_y: 28.5 },
      "서산시":  { geo_x: 33.5, geo_y: 33.5 }, "논산시":  { geo_x: 44.5, geo_y: 41.0 },
      "계룡시":  { geo_x: 46.0, geo_y: 40.5 }, "당진시":  { geo_x: 36.5, geo_y: 28.5 },
      "금산군":  { geo_x: 49.5, geo_y: 43.0 }, "부여군":  { geo_x: 41.5, geo_y: 41.5 },
      "서천군":  { geo_x: 39.0, geo_y: 44.5 }, "청양군":  { geo_x: 40.5, geo_y: 38.5 },
      "홍성군":  { geo_x: 37.5, geo_y: 36.0 }, "예산군":  { geo_x: 40.0, geo_y: 33.5 },
      "태안군":  { geo_x: 29.5, geo_y: 32.5 },
    },
  },
  "전북특별자치도": {
    center: { geo_x: 43.0, geo_y: 53.0 },
    sigungu: {
      "전주시":  { geo_x: 43.0, geo_y: 52.5 }, "군산시":  { geo_x: 37.5, geo_y: 49.0 },
      "익산시":  { geo_x: 40.5, geo_y: 49.5 }, "정읍시":  { geo_x: 40.5, geo_y: 55.5 },
      "남원시":  { geo_x: 46.5, geo_y: 58.5 }, "김제시":  { geo_x: 40.0, geo_y: 52.5 },
      "완주군":  { geo_x: 43.5, geo_y: 51.0 }, "진안군":  { geo_x: 48.5, geo_y: 53.0 },
      "무주군":  { geo_x: 51.5, geo_y: 51.5 }, "장수군":  { geo_x: 50.0, geo_y: 56.5 },
      "임실군":  { geo_x: 45.5, geo_y: 56.5 }, "순창군":  { geo_x: 43.5, geo_y: 59.0 },
      "고창군":  { geo_x: 38.5, geo_y: 57.5 }, "부안군":  { geo_x: 37.5, geo_y: 53.0 },
    },
  },
  "전라남도": {
    center: { geo_x: 39.8, geo_y: 67.5 },
    sigungu: {
      "목포시":  { geo_x: 34.5, geo_y: 70.5 }, "여수시":  { geo_x: 48.5, geo_y: 73.5 },
      "순천시":  { geo_x: 47.0, geo_y: 70.0 }, "나주시":  { geo_x: 38.5, geo_y: 66.5 },
      "광양시":  { geo_x: 50.0, geo_y: 70.5 }, "담양군":  { geo_x: 41.0, geo_y: 62.5 },
      "곡성군":  { geo_x: 45.0, geo_y: 64.0 }, "구례군":  { geo_x: 48.0, geo_y: 65.5 },
      "고흥군":  { geo_x: 46.5, geo_y: 75.5 }, "보성군":  { geo_x: 44.0, geo_y: 71.5 },
      "화순군":  { geo_x: 41.5, geo_y: 67.5 }, "장흥군":  { geo_x: 42.0, geo_y: 73.5 },
      "강진군":  { geo_x: 40.0, geo_y: 74.5 }, "해남군":  { geo_x: 37.5, geo_y: 76.5 },
      "영암군":  { geo_x: 37.0, geo_y: 71.5 }, "무안군":  { geo_x: 35.5, geo_y: 68.5 },
      "함평군":  { geo_x: 36.5, geo_y: 65.5 }, "영광군":  { geo_x: 34.5, geo_y: 62.5 },
      "장성군":  { geo_x: 38.0, geo_y: 62.0 }, "완도군":  { geo_x: 41.5, geo_y: 78.5 },
      "진도군":  { geo_x: 32.0, geo_y: 76.5 }, "신안군":  { geo_x: 31.0, geo_y: 70.5 },
    },
  },
  "경상북도": {
    center: { geo_x: 69.5, geo_y: 40.5 },
    sigungu: {
      "포항시":  { geo_x: 78.5, geo_y: 43.5 }, "경주시":  { geo_x: 77.5, geo_y: 49.5 },
      "김천시":  { geo_x: 62.0, geo_y: 47.5 }, "안동시":  { geo_x: 70.0, geo_y: 34.5 },
      "구미시":  { geo_x: 64.5, geo_y: 45.0 }, "영주시":  { geo_x: 68.0, geo_y: 29.5 },
      "영천시":  { geo_x: 74.5, geo_y: 47.5 }, "상주시":  { geo_x: 62.5, geo_y: 40.5 },
      "문경시":  { geo_x: 61.5, geo_y: 36.5 }, "경산시":  { geo_x: 73.5, geo_y: 48.5 },
      "의성군":  { geo_x: 68.5, geo_y: 38.0 }, "청송군":  { geo_x: 73.0, geo_y: 35.0 },
      "영양군":  { geo_x: 75.5, geo_y: 31.5 }, "영덕군":  { geo_x: 77.5, geo_y: 34.5 },
      "청도군":  { geo_x: 72.0, geo_y: 52.0 }, "고령군":  { geo_x: 67.5, geo_y: 51.5 },
      "성주군":  { geo_x: 65.5, geo_y: 49.0 }, "칠곡군":  { geo_x: 67.0, geo_y: 46.5 },
      "예천군":  { geo_x: 65.5, geo_y: 34.5 }, "봉화군":  { geo_x: 71.5, geo_y: 27.5 },
      "울진군":  { geo_x: 80.0, geo_y: 28.5 }, "울릉군":  { geo_x: 97.0, geo_y: 22.0 },
    },
  },
  "경상남도": {
    center: { geo_x: 65.0, geo_y: 59.5 },
    sigungu: {
      "창원시":  { geo_x: 68.5, geo_y: 61.5 }, "진주시":  { geo_x: 61.5, geo_y: 64.5 },
      "통영시":  { geo_x: 65.5, geo_y: 69.0 }, "사천시":  { geo_x: 61.5, geo_y: 67.5 },
      "김해시":  { geo_x: 72.0, geo_y: 60.5 }, "밀양시":  { geo_x: 73.5, geo_y: 57.0 },
      "거제시":  { geo_x: 69.5, geo_y: 70.5 }, "양산시":  { geo_x: 75.5, geo_y: 59.0 },
      "의령군":  { geo_x: 65.5, geo_y: 62.5 }, "함안군":  { geo_x: 67.5, geo_y: 62.5 },
      "창녕군":  { geo_x: 68.5, geo_y: 57.5 }, "고성군":  { geo_x: 64.5, geo_y: 67.5 },
      "남해군":  { geo_x: 59.0, geo_y: 70.0 }, "하동군":  { geo_x: 55.5, geo_y: 67.0 },
      "산청군":  { geo_x: 58.5, geo_y: 63.0 }, "함양군":  { geo_x: 55.5, geo_y: 60.5 },
      "거창군":  { geo_x: 57.5, geo_y: 57.5 }, "합천군":  { geo_x: 63.5, geo_y: 57.5 },
    },
  },
  "제주특별자치도": {
    center: { geo_x: 30.0, geo_y: 92.0 },
    sigungu: {
      "제주시":  { geo_x: 29.5, geo_y: 90.5 },
      "서귀포시":{ geo_x: 30.5, geo_y: 93.5 },
    },
  },
};

/** sido + sigungu → 좌표 조회 (없으면 sido 중심 좌표 반환) */
export function getCoord(sido: string, sigungu?: string): DistrictCoord | null {
  const sidoData = DISTRICTS[sido];
  if (!sidoData) return null;
  if (sigungu && sidoData.sigungu[sigungu]) return sidoData.sigungu[sigungu];
  return sidoData.center;
}

/** sido 에 속한 sigungu 목록 반환 */
export function getSigunguList(sido: string): string[] {
  return Object.keys(DISTRICTS[sido]?.sigungu ?? {});
}
