!/bin/bash
if pgrep retroarc > /dev/null
then
    xdotool search --onlyvisible --all --name 'Retroarch' windowactivate
else
    retroarch
    xdotool search --onlyvisible --all --name 'Retroarch' windowactivate
fi
