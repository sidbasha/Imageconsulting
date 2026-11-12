/** Test double: a fixed position in Dubai, or a refusal when __deny is set. */
const state = { deny: false, position: { latitude: 25.2, longitude: 55.27 } };

const Geolocation = {
  getCurrentPosition: jest.fn((success: (p: any) => void, failure: (e: any) => void) => {
    if (state.deny) {
      failure({ code: 1, message: 'denied' });
    } else {
      success({ coords: { ...state.position, accuracy: 1000 } });
    }
  }),
  __state: state,
};

export default Geolocation;
