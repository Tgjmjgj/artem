# Artem

![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Version](https://img.shields.io/badge/version-1.11.03-brightgreen.svg)
![PyPI version](https://img.shields.io/badge/PyPI-v1.11.03-brightgreen.svg)
![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)
![License](https://img.shields.io/badge/license-apache-yellow.svg)

## <span style="color: #660000">Yes, this is another deprecated project.</span>

## _Simple core for creating chatbots in VK (vk.com)_

Artem is an easy core for creating chatbots in _vk.com_ based on the flexible mechanism of user scenarios for replies.

<br>

## Installing artem

To install artem through pip, execute follow command:

```bash
pip install artem
```

Also you can download the package from [Python Package Index](https://pypi.python.org/pypi/artem/) or [Github Releases](https://github.com/Tgjmjgj/artem/releases), unzip archive and use this command for install:

```bash
python setup.py install
```

## Start of use

The simplest example of launching:

```python
import artem

art = artem.Artem(GROUP_ID, GROUP_ACCESS_KEY)
art.on('MESSAGE', handler='Hello World from Artem!')
art.alive()
```

After running this script, the bot-chat will answer any incoming message with the words "Hello World from Artem!". For more, see below.

## Description of the artem core

### Artem core

The simplified scheme of the Artem core functioning:

<img src = "https://s3-eu-west-1.amazonaws.com/images.someone.new.name/artemS.png" width=600 alt="Artem Scheme" style="text-align: center;" />

### Artem events

Artem has three groups of handled scenarios:

1. Scenarios of incoming events:
    * JOIN
    * MESSAGE
2. Scenarios of time events:
    * TIME
    * IDLE
    * SILENCE
3. Scenarios for postprocessing events:
    * POSTPROC
4. Startup scenario:
    * START

Full event Handling Schema:

<img src="https://s3-eu-west-1.amazonaws.com/images.someone.new.name/artem_events.png" alt="Artem events" style="text-align: center;" />