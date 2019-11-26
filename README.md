# snitch

Simple python script for get event notifications from GitLab and Jira... if your team don't want make something more convenient ;)

Can be launched (for example) from cron job: 

```
0 * * * *  /path/to/snitch/snitch.py
```

It is reasonable to set the period of cron task equal to a variable `mins-ago`
