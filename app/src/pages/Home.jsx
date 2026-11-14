import SiteNav from '@/components/SiteNav';
import SiteFooter from '@/components/SiteFooter';
import HeroSignal from '@/components/sections/HeroSignal';
import ChannelTopology from '@/components/sections/ChannelTopology';
import ConversionStream from '@/components/sections/ConversionStream';
import HardwareSpec from '@/components/sections/HardwareSpec';
import Pipeline from '@/components/sections/Pipeline';
import InvestorCase from '@/components/sections/InvestorCase';
import Roadmap from '@/components/sections/Roadmap';
import DeveloperSdk from '@/components/sections/DeveloperSdk';
import AccessForm from '@/components/sections/AccessForm';

export default function Home() {
  return (
    <div id="top" className="min-h-screen bg-[#050505] text-[#F2F2F2]">
      <SiteNav />
      <main>
        <HeroSignal />
        <ChannelTopology />
        <ConversionStream />
        <HardwareSpec />
        <Pipeline />
        <InvestorCase />
        <Roadmap />
        <DeveloperSdk />
        <AccessForm />
      </main>
      <SiteFooter />
    </div>
  );
}