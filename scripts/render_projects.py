# SPDX-License-Identifier: Apache-2.0
# This script creates renders of all the projects on a given Tiny Tapeout shuttle.
# Copyright (C) 2024 Tiny Tapeout LTD
# Author: Uri Shaked

import argparse
import json
import logging
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from klayout.db import Layout, SaveLayoutOptions
from klayout.lay import LayoutView

SCRIPT_DIR = Path(__file__).parent

TECHNOLOGIES = {
    "sky130A": {
        "boundary": "prBoundary.boundary",
        "hide_layers": ["areaid.standardc", "areaid.lowTapDensity"],
    },
    "sg13g2": {
        "boundary": "235/4",
        "hide_layers": ["235/4"],
    },
}


def download_gds(shuttle_id: str, macro: str) -> Path:
    target_path = SCRIPT_DIR / "gds" / shuttle_id / f"{macro}.gds"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        logging.info(f"Found existing GDS file at {target_path}, skipping download")
        return target_path

    # Download the main index file from the Tiny Tapeout server
    url = "https://index.tinytapeout.com/index.json"
    logging.info(f"Downloading index file from {url}")
    response = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    )
    index = json.load(response)
    shuttles = index.get("shuttles", {})
    shuttle = next(
        (shuttle for shuttle in shuttles if shuttle["id"] == shuttle_id), None
    )
    if not shuttle:
        logging.error(f"Shuttle {shuttle_id} not found in the index")
        sys.exit(1)

    gds_url = shuttle["project_gds_url_template"].format(macro=macro)
    is_rom = macro == "tt_um_chip_rom"
    if is_rom:
        gds_url = shuttle["gds_url"]
    logging.info(f"Downloading GDS file from {gds_url}")

    response = urllib.request.urlopen(gds_url)
    with open(target_path, "wb") as f:
        if gds_url.endswith(".gz"):
            import gzip

            with gzip.GzipFile(fileobj=response) as gz:
                f.write(gz.read())
        else:
            f.write(response.read())

    if is_rom:
        layout = Layout()
        layout.read(target_path)
        for cell in layout.each_cell():
            if cell.name == "tt_um_chip_rom" or cell.name.endswith("_tt_um_chip_rom"):
                rom_cell = cell
        if not rom_cell:
            raise Exception("ROM cell not found")
        save_options = SaveLayoutOptions()
        save_options.add_cell(rom_cell.cell_index())
        layout.write(target_path, options=save_options)

    return target_path


def render_gds(
    gds_path: str,
    output_path: str,
    pdk: str,
    scale: float = 1.0,
):
    BOUNDARY_LAYER = TECHNOLOGIES[pdk]["boundary"]
    hide_layers = TECHNOLOGIES[pdk]["hide_layers"]

    lv = LayoutView()
    lv.load_layout(gds_path)
    lv.max_hier()
    lv.load_layer_props(SCRIPT_DIR / "lyp" / f"{pdk}.lyp")

    lv.set_config("background-color", "#ffffff")
    lv.set_config("grid-visible", "false")
    lv.set_config("text-visible", "false")
    lv.zoom_fit()

    bbox = None
    for layer in lv.each_layer():
        layer_name = layer.name
        if pdk == "sky130A":
            layer_name = layer.name.split("-")[0].strip() if "-" else ""
        if layer_name == "":
            layer_name = f"{layer.source_layer}/{layer.source_datatype}"
        if layer_name == BOUNDARY_LAYER:
            bbox = layer.bbox()
            layer.visible = layer_name not in hide_layers
        elif hide_layers is not None:
            layer.visible = layer_name not in hide_layers and layer_name != ""
        else:
            layer.visible = layer_name != ""  # Hides the fill layers

    if bbox is None:
        raise ValueError(f"No bounding box found for '{BOUNDARY_LAYER}' layer")
    lv.zoom_box(bbox)

    lv.save_image(output_path, int(bbox.width() * scale), int(bbox.height() * scale))
    lv.destroy()


def main(shuttle_id: str, scale: float = 1.0):
    project_list_url = f"https://index.tinytapeout.com/{shuttle_id}.json"
    req = urllib.request.Request(
        project_list_url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req) as req:
        project_list = json.load(req)["projects"]
    logging.info(f"Found {len(project_list)} projects in shuttle {shuttle_id}")

    pdk = "sg13g2" if shuttle_id.startswith("ttihp") else "sky130A"

    for project in project_list:
        logging.info(f"Rendering {project['macro']}")
        gds_file = download_gds(shuttle_id, project["macro"])
        png_dir = SCRIPT_DIR / ".." / "shuttles" / shuttle_id / project["macro"]
        png_dir.mkdir(parents=True, exist_ok=True)

        logging.info(f"Rendering {png_dir / 'render.png'}")
        render_gds(
            gds_file,
            png_dir / "render.png",
            pdk=pdk,
            scale=scale,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update shuttle index")
    parser.add_argument("shuttle_id", type=str, help="Shuttle ID")
    parser.add_argument(
        "--scale",
        type=float,
        default=5.0,
        help="Scale factor for the output image",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    main(args.shuttle_id, scale=args.scale)
