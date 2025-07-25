import { z } from "zod";
import { customTypes } from "./custom_types";

export const viewTypeEnum = z
  .enum([
    "projects",
    "experiments",
    "experiment",
    "playgrounds",
    "playground",
    "datasets",
    "dataset",
    "prompts",
    "tools",
    "scorers",
    "logs",
    "agents",
    "monitor",
  ])
  .describe("Type of object that the view corresponds to.");
export type ViewType = z.infer<typeof viewTypeEnum>;

export const viewDataSearchSchema = z
  .object({
    filter: z.array(customTypes.unknown).nullish(),
    tag: z.array(customTypes.unknown).nullish(),
    match: z.array(customTypes.unknown).nullish(),
    sort: z.array(customTypes.unknown).nullish(),
  })
  .strip()
  .openapi("ViewDataSearch");
export const viewDataSchema = z
  .object({
    search: viewDataSearchSchema.nullish(),
  })
  .strip()
  .openapi("ViewData");
export type ViewData = z.infer<typeof viewDataSchema>;
const chartSelectionType = z.object({
  type: z.enum(["none", "score", "metric", "metadata"]),
  value: z.string(),
});
export const annotationDataSchema = z.object({
  id: z.string(),
  text: z.string(),
});

const allAggregationTypeEnum = z.enum([
  "avg",
  "sum",
  "min",
  "max",
  "median",
  "all",
]);

export const tableViewOptionsSchema = z
  .object({
    columnVisibility: z.record(z.boolean()).nullish(),
    columnOrder: z.array(z.string()).nullish(),
    columnSizing: z.record(z.number()).nullish(),
    grouping: z.string().nullish(),
    rowHeight: z.string().nullish(),
    tallGroupRows: z.boolean().nullish(),
    layout: z.string().nullish(),
    chartHeight: z.number().nullish(),
    excludedMeasures: z.array(chartSelectionType).nullish(),
    yMetric: chartSelectionType.nullish(),
    xAxis: chartSelectionType.nullish(),
    symbolGrouping: chartSelectionType.nullish(),
    xAxisAggregation: z
      .string()
      .pipe(allAggregationTypeEnum.catch("avg"))
      .describe(
        `One of ${allAggregationTypeEnum.options.map((opt) => `'${opt}'`).join(", ")}`,
      )
      .nullish(),
    chartAnnotations: z.array(annotationDataSchema).nullish(),
    timeRangeFilter: z
      .union([z.string(), z.object({ from: z.string(), to: z.string() })])
      .nullish(),
  })
  .strip()
  .openapi({ title: "TableViewOptions" });

export type TableViewOptions = z.infer<typeof tableViewOptionsSchema>;

export const monitorViewOptionsSchema = z
  .object({
    spanType: z.enum(["range", "frame"]).nullish(),
    rangeValue: z.string().nullish(),
    frameStart: z.string().nullish(),
    frameEnd: z.string().nullish(),
    tzUTC: z.boolean().nullish(),
    chartVisibility: z.record(z.boolean()).nullish(),
    projectId: z.string().nullish(),
    type: z.enum(["project", "experiment"]).nullish(),
    groupBy: z.string().nullish(),
  })
  .strip();

export type MonitorViewOptions = z.infer<typeof monitorViewOptionsSchema>;

export const viewOptionsSchema = z
  .union([
    // Monitor view with explicit type
    z
      .object({
        viewType: z.literal(viewTypeEnum.Values.monitor),
        options: monitorViewOptionsSchema,
      })
      .openapi({ title: "MonitorViewOptions" }),
    // All other views (legacy)
    tableViewOptionsSchema,
  ])
  .openapi("ViewOptions");

export type ViewOptions = z.infer<typeof viewOptionsSchema>;
