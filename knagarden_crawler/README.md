# 정원백과 Selenium 크롤러

정원백과 식물 목록에서 상세 페이지 링크를 수집한 뒤, 각 상세 페이지의 식물 정보를 JSON과 CSV로 저장하는 예시 코드입니다.

## 설치

```bash
cd knagarden_crawler
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Chrome이 설치되어 있으면 Selenium Manager가 드라이버를 자동으로 준비합니다.

## 테스트 실행

```bash
python knagarden_selenium_crawler.py --limit 5
```

## 1단계: 주소만 수집

```powershell
python .\collect_links.py --max-list-pages 52 --delay-min 20 --delay-max 45 --show-browser
```

결과는 `output/plant_links.txt`에 저장됩니다.

## 2단계: 주소 파일을 읽어서 상세 내용 수집

```powershell
python .\crawl_details.py --links-file output\plant_links.txt --delay-min 45 --delay-max 90 --blocked-sleep-min 300 --blocked-sleep-max 900 --show-browser
```

중간에 멈춰도 다시 같은 명령을 실행하면 이미 수집한 URL은 건너뜁니다.

## 목록 페이지를 더 많이 훑기

```bash
python knagarden_selenium_crawler.py --max-list-pages 20
```

## 브라우저 창을 보면서 실행

```bash
python knagarden_selenium_crawler.py --show-browser --limit 5
```

## 403이 중간중간 뜰 때

CloudFront 403 페이지가 뜨면 식물 데이터로 저장하지 않고, 긴 대기 후 같은 URL을 다시 시도합니다.

```bash
python knagarden_selenium_crawler.py --max-list-pages 52 --delay-min 45 --delay-max 90 --blocked-sleep-min 300 --blocked-sleep-max 900 --show-browser
```

재시도 후에도 실패한 URL은 `output/failed_urls.txt`에 기록됩니다.

## 결과물

기본적으로 `output` 폴더에 아래 파일이 생성됩니다.

- `plant_links.txt`: 수집한 상세 페이지 URL
- `knagarden_plants.json`: 원문 텍스트와 섹션별 텍스트를 포함한 JSON
- `knagarden_plants.csv`: 엑셀에서 열기 쉬운 CSV

## 메모

사이트가 자동 요청을 막을 수 있으니 요청 간격을 너무 짧게 두지 않는 편이 좋습니다. 기본값은 상세 페이지마다 2~5초 사이에서 임의 대기합니다.
