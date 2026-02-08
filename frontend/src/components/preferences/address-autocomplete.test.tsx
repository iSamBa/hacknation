import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";
import { AddressAutocomplete } from "./address-autocomplete";

const originalEnv = { ...process.env };

const mockPlace = {
  formatted_address: "123 Test Street, Paris",
  geometry: {
    location: {
      lat: () => 48.8566,
      lng: () => 2.3522,
    },
  },
};

let placeChangedCallback: (() => void) | null = null;

class MockAutocomplete {
  getPlace = vi.fn(() => mockPlace);
  addListener = vi.fn((_event: string, callback: () => void) => {
    placeChangedCallback = callback;
  });
}

const mockClearInstanceListeners = vi.fn();

function setupGoogleMock() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).google = {
    maps: {
      places: {
        Autocomplete: MockAutocomplete,
      },
      event: {
        clearInstanceListeners: mockClearInstanceListeners,
      },
    },
  };
}

function removeGoogleMock() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  delete (window as any).google;
}

beforeEach(() => {
  placeChangedCallback = null;
  document.getElementById("google-maps-script")?.remove();
});

afterEach(() => {
  cleanup();
  process.env = { ...originalEnv };
  removeGoogleMock();
});

describe("AddressAutocomplete", () => {
  const defaultProps = {
    value: "",
    onChange: vi.fn(),
    onAddressSelect: vi.fn(),
  };

  describe("without API key", () => {
    beforeEach(() => {
      delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    });

    it("renders a plain input as fallback", () => {
      render(<AddressAutocomplete {...defaultProps} />);
      expect(
        screen.getByPlaceholderText("Enter your address"),
      ).toBeInTheDocument();
    });

    it("displays the provided value", () => {
      render(<AddressAutocomplete {...defaultProps} value="123 Main St" />);
      expect(screen.getByDisplayValue("123 Main St")).toBeInTheDocument();
    });

    it("calls onChange when user types", () => {
      const onChange = vi.fn();
      render(<AddressAutocomplete {...defaultProps} onChange={onChange} />);
      fireEvent.change(screen.getByPlaceholderText("Enter your address"), {
        target: { value: "456 Oak Ave" },
      });
      expect(onChange).toHaveBeenCalledWith("456 Oak Ave");
    });
  });

  describe("with API key and Google Maps loaded", () => {
    beforeEach(() => {
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY = "test-api-key";
      setupGoogleMock();
    });

    it("renders an input that initializes autocomplete", async () => {
      await act(async () => {
        render(<AddressAutocomplete {...defaultProps} />);
      });

      const input = screen.getByRole("textbox");
      expect(input).toBeInTheDocument();
    });

    it("calls onAddressSelect when a place is selected", async () => {
      const onAddressSelect = vi.fn();
      const onChange = vi.fn();

      await act(async () => {
        render(
          <AddressAutocomplete
            {...defaultProps}
            onChange={onChange}
            onAddressSelect={onAddressSelect}
          />,
        );
      });

      expect(placeChangedCallback).not.toBeNull();
      act(() => {
        placeChangedCallback!();
      });

      expect(onChange).toHaveBeenCalledWith("123 Test Street, Paris");
      expect(onAddressSelect).toHaveBeenCalledWith({
        address: "123 Test Street, Paris",
        latitude: 48.8566,
        longitude: 2.3522,
      });
    });

    it("does not call onAddressSelect when place has no geometry", async () => {
      const onAddressSelect = vi.fn();
      // Create a custom mock that returns no geometry
      const noGeoMock = new MockAutocomplete();
      noGeoMock.getPlace = vi.fn(() => ({
        formatted_address: "Some address",
        geometry: null,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      })) as any;

      // Override the Autocomplete constructor for this test
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).google.maps.places.Autocomplete = class {
        getPlace = noGeoMock.getPlace;
        addListener = vi.fn((_event: string, callback: () => void) => {
          placeChangedCallback = callback;
        });
      };

      await act(async () => {
        render(
          <AddressAutocomplete
            {...defaultProps}
            onAddressSelect={onAddressSelect}
          />,
        );
      });

      expect(placeChangedCallback).not.toBeNull();
      act(() => {
        placeChangedCallback!();
      });

      expect(onAddressSelect).not.toHaveBeenCalled();
    });

    it("allows typing in the autocomplete input", async () => {
      const onChange = vi.fn();

      await act(async () => {
        render(<AddressAutocomplete {...defaultProps} onChange={onChange} />);
      });

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "New address" } });
      expect(onChange).toHaveBeenCalledWith("New address");
    });
  });
});
