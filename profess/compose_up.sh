echo "Building the Optimization Framework"
sudo docker-compose -f docker-compose-arm.yml build ofw
echo "Starting the Optimization Framework"
sudo docker-compose -f docker-compose-arm.yml up ofw
