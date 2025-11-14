import { render, screen } from "@testing-library/react";
import ImportFile from "./components/ImportFile";

jest.mock("axios", () => ({
  __esModule: true,
  default: {
    post: jest.fn(() => Promise.resolve({ data: { message: "ok" } })),
  },
  post: jest.fn(() => Promise.resolve({ data: { message: "ok" } })),
}));

test("renders multi-file upload controls", () => {
  render(<ImportFile />);
  expect(
    screen.getByRole("button", { name: /selecionar arquivos/i })
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /enviar fila/i })).toBeDisabled();
});
