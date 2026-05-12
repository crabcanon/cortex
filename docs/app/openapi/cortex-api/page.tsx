import type { Metadata } from "next";
import CortexSwaggerUi from "./swagger-ui";

export const metadata: Metadata = {
  title: "Cortex OpenAPI Specs",
  description: "Interactive Swagger UI renderer for the Cortex OpenAPI contract.",
};

export default function CortexOpenApiPage() {
  return <CortexSwaggerUi specUrl="/openapi/cortex-api.yaml" />;
}
