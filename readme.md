# DMARC Extractor

## How to Use

1. **Create Environment File**
    - Create an `.env` file with your credentials, following the structure provided in `env_template`.

2. **Extract Attachments**
    - Run the script `extract_attachments.py` to extract email attachments.

    ```bash
    python extract_attachments.py
    ```

3. **Unzip Attachments**
    - Run the script `unzip_attachments.py` to unzip the extracted attachments.

    ```bash
    python unzip_attachments.py
    ```

4. **Analyze DMARC Reports**
    - Run the script `dmarc_analyzer.py` to analyze the DMARC reports.

    ```bash
    python dmarc_analyzer.py
    ```

5. **Browse DMARC Analyzer**
    - Open your web browser and go to `http://localhost:5000` to view the DMARC analyzer.

## Requirements

- Python 3.x
- Required Python packages (install via `requirements.txt`)

```bash
cd /path/to/your/project
python3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## License

This project is licensed under the MIT License.
