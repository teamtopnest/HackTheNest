import SiteNav from '@/components/SiteNav';
import SiteFooter from '@/components/SiteFooter';
import HeroSignal from '@/components/sections/HeroSignal';
import ChannelTopology from '@/components/sections/ChannelTopology';
import ConversionStream from '@/components/sections/ConversionStream';
import HardwareSpec from '@/components/sections/HardwareSpec';
import Pipeline from '@/components/sections/Pipeline';
import Roadmap from '@/components/sections/Roadmap';
import AccessForm from '@/components/sections/AccessForm';

export default function Home() {
  return (
    <div id="top" className="min-h-screen bg-[#07111B] text-[#F8FAFC]">
      <SiteNav />
      <main>
        <HeroSignal />
        <ChannelTopology />
        <ConversionStream />
        <HardwareSpec />
        <Pipeline />
        <Roadmap />
        <AccessForm />
      </main>
      <SiteFooter />
    </div>
  );
}
