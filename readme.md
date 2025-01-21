# DMARC Extractor

## How to Use

1. **Create Environment File**
    - Create an `.env` file with your credentials, following the structure provided in `config_template`.

2. **Extract Attachments**
    - If you're using Microsoft 365, please follow the instructions at the bottom (Chapter "Using Microsoft 365").
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

## Using Microsoft 365

When you're using Microsoft 365, you first need to register the application in your tenant.
- Go to https://entra.microsoft.com and log in using an administrator.
- Go to Applications -> App registrations
- Create a new registration
- Enter a name and choose "Accounts in this organizational directory only"
- Select Web as a platform and enter `http://localhost:5000/callback` as the callback URI
- Go to Certificates & Secrets and create a new secret key for the application. Copy the key and enter it into the .env-file.

- You're now able to start the application using the script `extract_attachments_M365.py`

    ```bash
    python extract_attachments_M365.py
    ```

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
