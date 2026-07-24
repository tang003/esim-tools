import QRCode from 'qrcode';

export async function toQrDataUrl(text: string): Promise<string> {
  return QRCode.toDataURL(text, {
    width: 260,
    margin: 2,
    color: {
      dark: '#17243a',
      light: '#ffffff'
    }
  });
}

