# hl-downloader
This project downloads all content from ost.hacking-lab.com and creates a folder structure as follow:
```
event
   challenge
      Curriculum Event
         media
            picture01.png
         comments 
            attachment01.pdf
         resources
            resources01.txt
```
## Setup

Install the requirements
```python
pip install requirements.txt 
```

### Optional: Credentials file
The script loops up for a credentials file in `~\ ` and `.\ `  

Filename: `.hl-cred.json`
```json

{
  "username": "",
  "password": ""
}
```


## Usage 
Run
```
python3 main.py
```
