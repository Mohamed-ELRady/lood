import { DownloadWorkbench } from "@/components/download-workbench";
import { ServiceWorkerRegistration } from "@/components/service-worker";

export default function Home() {
  return (
    <>
      <ServiceWorkerRegistration />
      <DownloadWorkbench />
    </>
  );
}

