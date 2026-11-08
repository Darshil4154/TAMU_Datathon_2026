.PHONY: data test app check
data:
	python -m src.pipeline
test:
	python -m pytest -q
app:
	python -m streamlit run app.py
check: test
	python -m src.check
