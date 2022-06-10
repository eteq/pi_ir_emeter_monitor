// Writes out the GPIO at high speed in a densly-packed form for troubleshooting

use std::io::prelude::*;
use std::fs::OpenOptions;
use std::error::Error;
use std::time::Instant;
//use std::thread::sleep;
//use std::time::Duration;

use rppal::gpio;

const PULSE_PIN: u8 = 24; //BCM pin #
const N_SAMPLES: usize = 2000000;

fn main() -> Result<(), Box<dyn Error>>  {
    let log_path = "write_gpio.log";
    let mut outfile = OpenOptions::new().write(true).truncate(true).create(true).open(log_path)?;

    let g = gpio::Gpio::new()?;
    let pin = g.get(PULSE_PIN)?.into_input();

    let mut b: [u8; N_SAMPLES] = [0; N_SAMPLES];

    let start = Instant::now();
    for i in 0..N_SAMPLES {
        b[i] = pin.is_high() as u8;
        //sleep(Duration::from_micros(1));
    }
    let end = Instant::now();
    let nanos = end.duration_since(start).as_nanos();
    println!("{} samples in {} ns, equivalent to a sample rate of {} Hz", N_SAMPLES, nanos, N_SAMPLES as f64 / nanos as f64 * 1e9 as f64);

    let mut ntrue : usize = 0;
    outfile.write(&b)?;
    for i in 0..N_SAMPLES {
        if b[i] == 1 { ntrue +=1; }
    }
    println!("{} true of {}", ntrue, N_SAMPLES);


    Ok(())
}
