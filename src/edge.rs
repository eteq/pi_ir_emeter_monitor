use std::error::Error;
use std::time::{SystemTime, Duration};

use rppal::gpio;

const PULSE_PIN: u8 = 24; //BCM pin #

fn main() -> Result<(), Box<dyn Error>> {
    let g = gpio::Gpio::new()?;
    let mut pin = g.get(PULSE_PIN)?.into_input();
    pin.set_interrupt(gpio::Trigger::Both)?;
    
    let t1 = SystemTime::now();
    let mut tlast = t1;
    loop {
        let level = match pin.poll_interrupt(true, Some(Duration::new(120, 0)))? {
            Some(l) => l,
            None => {break;}
        };
        let tloop = SystemTime::now();
        let fromstart =  tloop.duration_since(t1)?;
        let delta =  tloop.duration_since(tlast)?;

        let edgetype = if level == gpio::Level::High { "rising" } else { "falling" };
        println!("{} edge at: {} ms, delta from last: {} ms", edgetype, fromstart.as_millis(), delta.as_millis());
        
        tlast = tloop;
    }

    println!("Timed out waiting for a pulse");
    Ok(())
}