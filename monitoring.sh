#!/usr/bin/bash
#
# Some basic monitoring functionality; Tested on Amazon Linux 2.
#
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)
#https://geeksforgeeks.org/linux-system-monitoring-commands-and-tools/
DISK_PERFORMANCE=$(iostat -dx | awk 'NR==4 {print $NF"%"}') #gets I/O statistics, selecting the 4th line, grabs the last field which is the percentage of time the disc is doing operations
NETSTAT_CONNECTIONS=$(netstat -an | grep -c ESTABLISHED) #lists all connections in numberic format, counts all connections in the ESTABLISHED state
LOGGED_IN=$(who | wc -l) #count of how many users are logged in
UPTIME=$(uptime -p) #how long the system has been running

echo "//////////////////// START OF MONITORING.SH ////////////////////"
echo "Instance ID: $INSTANCE_ID"
echo "Memory utilisation: $MEMORYUSAGE"
echo "No of processes: $PROCESSES"
echo "Disk performace: $DISK_PERFORMANCE"
echo "Established network connections: $NETSTAT_CONNECTIONS"
echo "Logged in users: $LOGGED_IN"
echo "System uptime: $UPTIME"
if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi
echo "//////////////////// END OF MONITORING.SH ////////////////////"
