#!/usr/bin/bash
#
# Some basic monitoring functionality; Tested on Amazon Linux 2
# CPU usage ref: https://www.unix.com/unix-for-beginners-questions-and-answers/283279-required-cpu-memory-df-output-mail-multiple-servers.html
# Routing table ref: https://geekflare.com/linux-performance-commands/

INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)
SSH_PROCESSES=$(ps -A | grep -c ssh)
ROUTING_TABLE=$(netstat -r)
CPU_USAGE=$(top -bn1 | grep load | awk '{printf "CPU Usage: %.2f\n", $(NF-2)}')

echo "Instance ID: $INSTANCE_ID"
echo "Memory utilisation: $MEMORYUSAGE"
echo "$CPU_USAGE%"
echo "No of processes: $PROCESSES"
if [ $SSH_PROCESSES ]
then
    echo "ssh processes are running"
else
    echo "No ssh processes found"
fi

if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi
