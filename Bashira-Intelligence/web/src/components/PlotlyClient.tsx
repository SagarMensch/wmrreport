"use client";

import type { ComponentType } from "react";
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";

const Plot = createPlotlyComponent(Plotly) as unknown as ComponentType<any>;

export default Plot;
