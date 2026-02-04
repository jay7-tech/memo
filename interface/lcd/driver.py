import time
import spidev
import lgpio
from PIL import Image
import math
import numpy as np

# Pin Definitions (BCM)
PIN_DC = 25
PIN_RST = 24
PIN_BL = 17
PIN_CS = 8  # SPI0 CE0

# SPI Configuration
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED_HZ = 16000000 # Lowered to 16MHz for stability (40MHz is too fast for jumper wires)

class LCD_ST7735:
    def __init__(self, width=128, height=128, rotation=90):
        self.width = width
        self.height = height
        self.rotation = rotation
        
        # ST7735 1.44" often has an offset because the controller is 132x162
        # Adjust these if the image is shifted
        self.offset_x = 2
        self.offset_y = 3
        
        # Initialize GPIO
        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.h, PIN_DC, 0)
        lgpio.gpio_claim_output(self.h, PIN_RST, 1)
        
        try:
            lgpio.gpio_claim_output(self.h, PIN_BL, 1) # Backlight ON
        except:
            pass 
            
        # Initialize SPI
        self.spi = spidev.SpiDev()
        self.spi.open(SPI_BUS, SPI_DEVICE)
        self.spi.max_speed_hz = SPI_SPEED_HZ
        self.spi.mode = 0b00

        self.reset()
        self.init_display()

    def reset(self):
        """Hardware reset"""
        lgpio.gpio_write(self.h, PIN_RST, 1)
        time.sleep(0.01)
        lgpio.gpio_write(self.h, PIN_RST, 0)
        time.sleep(0.01)
        lgpio.gpio_write(self.h, PIN_RST, 1)
        time.sleep(0.120)

    def write_cmd(self, cmd):
        lgpio.gpio_write(self.h, PIN_DC, 0) # Command mode
        self.spi.writebytes([cmd])

    def write_data(self, data):
        lgpio.gpio_write(self.h, PIN_DC, 1) # Data mode
        if isinstance(data, list):
            self.spi.writebytes(data)
        elif isinstance(data, (bytes, bytearray)):
            self.spi.writebytes(data)
        else:
            self.spi.writebytes([data])

    def init_display(self):
        """Initialize ST7735 display (Green Tab 128x128 Standard)"""
        # SWRESET
        self.write_cmd(0x01)
        time.sleep(0.150)
        
        # SLPOUT
        self.write_cmd(0x11)
        time.sleep(0.200)
        
        # FRMCTR1 (Frame Rate Control) - Standard values
        self.write_cmd(0xB1)
        self.write_data([0x01, 0x2C, 0x2D])
        
        # FRMCTR2
        self.write_cmd(0xB2)
        self.write_data([0x01, 0x2C, 0x2D])
        
        # FRMCTR3
        self.write_cmd(0xB3)
        self.write_data([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])
        
        # INVCTR (Display Inversion Control)
        self.write_cmd(0xB4)
        self.write_data(0x07)
        
        # PWCTR1 (Power Control 1)
        self.write_cmd(0xC0)
        self.write_data([0xA2, 0x02, 0x84])
        
        # PWCTR2 (Power Control 2)
        self.write_cmd(0xC1)
        self.write_data(0xC5)
        
        # PWCTR3 (Power Control 3)
        self.write_cmd(0xC2)
        self.write_data([0x0A, 0x00])
        
        # PWCTR4 (Power Control 4)
        self.write_cmd(0xC3)
        self.write_data([0x8A, 0x2A])
        
        # PWCTR5 (Power Control 5)
        self.write_cmd(0xC4)
        self.write_data([0x8A, 0xEE])
        
        # VMCTR1 (VCOM Control 1)
        self.write_cmd(0xC5)
        self.write_data(0x0E)
        
        # INVOFF (Inversion Off) - Correct for Green Tab? Usually off.
        # Use 0x20 for Off, 0x21 for On. User reported white, so try Inv On first?
        # Let's stick to standard Green Tab which usually needs Inversion OFF (0x20)
        # BUT many clones need Inversion ON (0x21). I'll default to 0x21 (On) as it fixes the 'White Ghost'
        self.write_cmd(0x21) 
        
        # MADCTL - Memory Access Control (BGR color)
        self.write_cmd(0x36)
        self.write_data(0xC8) # 0xC8 = MY, MX, BGR
        
        # COLMOD - 16-bit color
        self.write_cmd(0x3A)
        self.write_data(0x05) 
        
        # CASET (Column Address Set)
        self.write_cmd(0x2A)
        self.write_data([0x00, 0x02, 0x00, 0x81]) # 2 to 129 (128w)
        
        # RASET (Row Address Set)
        self.write_cmd(0x2B)
        self.write_data([0x00, 0x01, 0x00, 0x80]) # 1 to 128 (128h)
        
        # GMCTRP1 (Gamma)
        self.write_cmd(0xE0)
        self.write_data([0x02, 0x1C, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2D, 0x29, 0x25, 0x2B, 0x39, 0x00, 0x01, 0x03, 0x10])
        
        # GMCTRN1 (Gamma)
        self.write_cmd(0xE1)
        self.write_data([0x03, 0x1D, 0x07, 0x06, 0x2E, 0x2C, 0x29, 0x2D, 0x2E, 0x2E, 0x37, 0x3F, 0x00, 0x00, 0x02, 0x10])
        
        # DISPON
        self.write_cmd(0x29)
        time.sleep(0.100)

    def set_window(self, x_start, y_start, x_end, y_end):
        # Adjust for offset
        x_start += self.offset_x
        x_end += self.offset_x
        y_start += self.offset_y
        y_end += self.offset_y
        
        # CASET
        self.write_cmd(0x2A)
        self.write_data([x_start >> 8, x_start & 0xFF, x_end >> 8, x_end & 0xFF])
        
        # RASET
        self.write_cmd(0x2B)
        self.write_data([y_start >> 8, y_start & 0xFF, y_end >> 8, y_end & 0xFF])
        
        # RAMWR
        self.write_cmd(0x2C)

    def display_image(self, image):
        """Send PIL Image to display"""
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Software Rotation
        if self.rotation != 0:
            image = image.rotate(self.rotation)

        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
            
        img_data = np.array(image, dtype=np.uint16)
        
        # RGB888 -> RGB565
        r = (img_data[:, :, 0] >> 3).astype(np.uint16)
        g = (img_data[:, :, 1] >> 2).astype(np.uint16)
        b = (img_data[:, :, 2] >> 3).astype(np.uint16)
        
        rgb565 = (r << 11) | (g << 5) | b
        
        rgb565_high = (rgb565 >> 8).astype(np.uint8)
        rgb565_low = (rgb565 & 0xFF).astype(np.uint8)
        
        packed = np.dstack((rgb565_high, rgb565_low)).flatten()
        
        self.set_window(0, 0, self.width - 1, self.height - 1)
        
        lgpio.gpio_write(self.h, PIN_DC, 1)
        
        # Chunk transfer
        data_bytes = packed.tobytes()
        chunk_size = 4096
        for i in range(0, len(data_bytes), chunk_size):
            self.spi.writebytes(data_bytes[i:i+chunk_size])

    def close(self):
        self.spi.close()
        lgpio.gpio_write(self.h, PIN_BL, 0)
        lgpio.gpiochip_close(self.h)
