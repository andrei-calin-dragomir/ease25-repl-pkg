cd EnergiBridge/

sudo chgrp -R $USER /dev/cpu/*/msr
sudo chmod g+r /dev/cpu/*/msr
cargo build -r
sudo setcap cap_sys_rawio=ep ./target/release/energibridge

# Install Codon
/bin/bash -c "$(curl -fsSL https://exaloop.io/install.sh)"

# Install Pypy
sudo apt install pypy3-dev

