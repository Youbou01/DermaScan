import type { ImageSourcePropType } from 'react-native';
import bodyLotion from '../../../assets/home/body-lotion.png';
import cleanser from '../../../assets/home/cleanser.png';
import eyeCare from '../../../assets/home/eye-care.png';
import lipCare from '../../../assets/home/lip-care.png';
import moisturizer from '../../../assets/home/moisturizer.png';
import serum from '../../../assets/home/serum.png';
import sunscreen from '../../../assets/home/sunscreen.png';
import toner from '../../../assets/home/toner.png';

const artworkByCategory: Record<string, ImageSourcePropType> = {
  'body-lotion': bodyLotion,
  cleanser,
  'eye-care': eyeCare,
  'lip-care': lipCare,
  moisturizer,
  serum,
  sunscreen,
  toner,
};

export function getProductArtwork(categorySlug: string | null): ImageSourcePropType | undefined {
  return categorySlug ? artworkByCategory[categorySlug] : undefined;
}
