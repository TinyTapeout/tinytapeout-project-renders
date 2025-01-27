# Tiny Tapeout Project Renders

This repo contains the GDS renders for all user projects submitted to Tiny Tapeout since Tiny Tapeout 2. The renders are generated using [klayout](https://www.klayout.org/).

## Regenerating the renders

To regenerate the PNG files for a shuttle, run the following commands:

```bash
cd scripts
pip install -r requirements.txt
python render_projects.py <shuttle>
```

Where `<shuttle>` is the identifier of the shuttle (e.g. tt04).

You can also specify the scale of the render by passing the `--scale` argument. For example, to render the all the projects in shuttle tt04 at 2x scale, run:

```bash
python render_projects.py tt04 --scale 2
```

## Generating glTF files

To generate glTF files for the projects, run the following commands:

```bash
git submodule update --init --recursive
cd scripts
pip install -r requirements.txt -r GDS2glTF/requirements.txt
python render_gltf.py <shuttle>
```

## License

The chip renders are licensed under the [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) license.