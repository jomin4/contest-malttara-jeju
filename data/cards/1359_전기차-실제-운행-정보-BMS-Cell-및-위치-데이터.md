---
id: 1359
title: "전기차 실제 운행 정보(BMS, Cell) 및 위치 데이터"
category: "교통, 안전"
type: "링크"
period_meta: "2022-11-15 ~ 2024-11-05"
period_actual: ""
auto_update: false
update_cycle: ""
spatial: "좌표"
temporal: "시점(스냅샷)"
join_keys: []
themes: ["교통·도로·안전", "전기차·모빌리티"]
series: ""
owner: "(주)타오스-개발팀"
status: "meta-only"
url: "https://jejudatahub.net/data/view/data/1359"
---

# 전기차 실제 운행 정보(BMS, Cell) 및 위치 데이터

## 요약

- 교통, 안전 분야, 제공형태 **링크**, 수집기간(메타) 2022-11-15 ~ 2024-11-05
- 단위(추정): 공간 좌표 · 시간 시점(스냅샷)
- 제공처: (주)타오스-개발팀 / 조회수 795 / 등록 2024-11-07 · 수정 2024-11-07
- 태그: #차량 #도로 #운전

### 원문 설명

전기차량(현대 아이오닉5, Kia RAY EV)의 주행 데이터(위치정보, BMS, Cell) 17만 건(아이오닉5 7만 건, RAY EV 10만 건).

JSON 파일 형식:
    _id: 데이터 식별자
    created: 데이터 저장 일시
    uservehicleinfo: 차량 식별자
    parsedData: 변환된 차량 데이터
    - parsedData.BMS: 변환된 차량 데이터 중 BMS 관련 정보
    - parsedData.BMS_Cell: 변환된 차량 데이터 중 Cell 관련 정보(전압)

데이터 유닛 형식: {
  FieldName: 데이터 항목 이름,
  DATA: 필드 값,
  Unit: 단위,
  Min: 최소값(범위),
  Max: 최대값(범위)
}


csv파일 설명:
JSON파일을 csv파일로 변환
fieldname으로만 이루어진 헤더의 컬럼은 값을 나타내며,
fieldname.Unit은 단위표시
fieldname.Min은 최솟값
fieldname.Max는 최댓값을 의미한다.

RAY EV의 경우는 2022년도 11월 16일부터 2024년도 11월 5일까지의 데이터를 포함한다.
아이오닉5의 경우는 2024년도 10월 18일부터 11월 05일까지의 데이터를 포함한다.

## 수집 방법

- **링크(외부 원본)**: https://drive.google.com/drive/folders/10vcmglSYE7rzdHAoepEMQfWTeGIvRy2r?usp=drive_link

## 컬럼

created, location.lat, location.lng, uservehicleinfo, Average_Cell_Voltage, Estimated_time_2.3kW_80%_Charge, Estimated_time_3.7kW_80%_Charge, Estimated_time_7.4kW_80%_Charge, Estimated_time_11kW_80%_Charge, Estimated_time_50kW_80%_Charge, Estimated_time_100kW_80%_Charge, Estimated_time_150kW_80%_Charge, Estimated_time_175kW_80%_Charge, Estimated_time_350kW_80%_Charge, Airbag_H/wire_Duty, Auxillary_Battery_Voltage, Available_Charge_Power, Available_Discharge_Power, Battery_Cell_Voltage_Deviation, Battery_Current, Battery_DC_Voltage, Battery_Power, BMS_Ignition, BMS_Main_Relay, Cumulative_Charge_Current, Cumulative_Discharge_Current, Cumulative_Energy_Charged, Cumulative_Energy_Discharged, Drive_Motor_Speed_1, Drive_Motor_Speed_2, HV_Charging, Inverter_Capacitor_Voltage, Isolation_Resistance, Maximum_Cell_Voltage, Maximum_Cell_Voltage_No, Maximum_Deterioration_Cell_No, Minimum_Cell_Voltage, Minimum_Cell_Voltage_No, Minimum_Deterioration

## 샘플 (미리보기 최대 5행)

|  | created | location.lat | location.lng | uservehicleinfo | Average_Cell_Voltage | Estimated_time_2.3kW_80%_Charge | Estimated_time_3.7kW_80%_Charge | Estimated_time_7.4kW_80%_Charge | Estimated_time_11kW_80%_Charge | Estimated_time_50kW_80%_Charge | Estimated_time_100kW_80%_Charge | Estimated_time_150kW_80%_Charge | Estimated_time_175kW_80%_Charge | Estimated_time_350kW_80%_Charge | Airbag_H/wire_Duty | Auxillary_Battery_Voltage | Available_Charge_Power | Available_Discharge_Power | Battery_Cell_Voltage_Deviation | Battery_Current | Battery_DC_Voltage | Battery_Power | BMS_Ignition | BMS_Main_Relay | Cumulative_Charge_Current | Cumulative_Discharge_Current | Cumulative_Energy_Charged | Cumulative_Energy_Discharged | Drive_Motor_Speed_1 | Drive_Motor_Speed_2 | HV_Charging | Inverter_Capacitor_Voltage | Isolation_Resistance | Maximum_Cell_Voltage | Maximum_Cell_Voltage_No | Maximum_Deterioration_Cell_No | Minimum_Cell_Voltage | Minimum_Cell_Voltage_No | Minimum_Deterioration |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1730777967 | 35.88473 | 128.7065 | 67116984d43a5412f18cbab4 | 4.08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 13.4 | 113.33 | 253 | 0 | 0.4 | 411.4 | 0.16 | 0 | 0 | 12281.7 | 11996.7 | 8986.9 | 8549.8 | 0 | 0 | 0 | 739 | 3000 | 4.08 | 84 | 0 | 4.08 | 157 | 3332.3 |
| 1 | 1730777965 | 35.88473 | 128.7065 | 67116984d43a5412f18cbab4 | 4.08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 13.4 | 113.33 | 253 | 0 | 0.5 | 411.4 | 0.21 | 0 | 0 | 12281.7 | 11996.7 | 8986.9 | 8549.8 | 0 | 0 | 0 | 739 | 3000 | 4.08 | 116 | 0 | 4.08 | 168 | 3332.3 |
| 2 | 1730777963 | 35.88473 | 128.7065 | 67116984d43a5412f18cbab4 | 4.08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 13.3 | 113.33 | 253 | 0 | 0.5 | 411.4 | 0.21 | 0 | 0 | 12281.7 | 11996.7 | 8986.9 | 8549.8 | 0 | 0 | 0 | 739 | 3000 | 4.08 | 81 | 0 | 4.08 | 50 | 3332.3 |
| 3 | 1730777961 | 35.88473 | 128.7065 | 67116984d43a5412f18cbab4 | 4.08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 13.3 | 113.33 | 253 | 0 | 0.6 | 411.4 | 0.25 | 0 | 0 | 12281.7 | 11996.7 | 8986.9 | 8549.8 | 0 | 0 | 0 | 739 | 3000 | 4.08 | 116 | 0 | 4.08 | 71 | 3332.3 |
| 4 | 1730777959 | 35.88473 | 128.7065 | 67116984d43a5412f18cbab4 | 4.08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 13.3 | 113.33 | 253 | 0 | 0.5 | 411.4 | 0.21 | 0 | 0 | 12281.7 | 11996.7 | 8986.9 | 8549.8 | 0 | 0 | 0 | 739 | 3000 | 4.08 | 119 | 0 | 4.08 | 134 | 3332.3 |

## 분석 결과

원본 미적재 (status: meta-only). 원본 수집·적재 후 scripts/profile.py가 행 수, 실제 기간, 결측, 상위 값을 채운다.

## 메모

<!-- notes:start -->
(메모 없음)
<!-- notes:end -->
