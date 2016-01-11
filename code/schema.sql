BEGIN TRANSACTION;

drop table if exists devices;

CREATE TABLE devices (
  id integer primary key autoincrement,
  name text not null,         --pref. name of device
  description text,           --device description, otpional
  type text not null,         --device type: input or output
  pin int,                    --pin the device uses
  state int,                  --only for output devices 0 = false, 1 = true, null for other devices
  module text                 --path to module of this device
);

INSERT INTO `devices` VALUES (1,'Temp Sensor 3000','best sensor in the universe','input',18,NULL,'modules/gpio_input.py');
INSERT INTO `devices` VALUES (2,'motor','best actor in the universe','input',16,NULL,'modules/gpio_input.py');
INSERT INTO `devices` VALUES (3,'led','bright led','output',11,0,'modules/gpio_output.py');
INSERT INTO `devices` VALUES (8,'led3','a zweite led','output',12,0,'modules/gpio_output.py');
INSERT INTO `devices` VALUES (9,'led35','onboard','output',35,0,'modules/gpio_output.py');
INSERT INTO `devices` VALUES (10,'led47','onboard','output',47,0,'modules/gpio_output.py');

COMMIT;
