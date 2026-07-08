import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import DateTimePicker from '@react-native-community/datetimepicker';

/**
 * Cross-platform date picker.
 * Value & onChange use ISO string "YYYY-MM-DD" (or "" when cleared).
 *
 * - Web: renders a styled <input type="date"> (native browser calendar).
 * - iOS/Android: opens the native DateTimePicker on tap.
 */
type Props = {
  value: string;              // "YYYY-MM-DD" or ""
  onChange: (iso: string) => void;
  placeholder?: string;
  minimumDate?: Date;
  maximumDate?: Date;
  testID?: string;
  disabled?: boolean;
};

const isoToDate = (iso: string): Date => {
  if (!iso) return new Date();
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return new Date();
  return new Date(y, m - 1, d);
};

const dateToIso = (d: Date): string => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
};

const formatDisplay = (iso: string): string => {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  if (!y || !m || !d) return iso;
  return `${d}/${m}/${y}`;
};

export const DateField: React.FC<Props> = ({
  value,
  onChange,
  placeholder = 'DD/MM/AAAA',
  minimumDate,
  maximumDate,
  testID,
  disabled,
}) => {
  const [showPicker, setShowPicker] = useState(false);
  const [tempDate, setTempDate] = useState<Date>(isoToDate(value));

  if (Platform.OS === 'web') {
    // Use native browser date input – fully accessible, keyboard-friendly.
    return (
      <View style={styles.wrap}>
        {/* @ts-ignore RN Web accepts DOM props via style hack */}
        <input
          type="date"
          value={value || ''}
          onChange={(e: any) => onChange(e.target.value || '')}
          disabled={disabled}
          data-testid={testID}
          style={{
            border: '1px solid #ddd',
            borderRadius: 8,
            padding: '10px 12px',
            fontSize: 15,
            backgroundColor: '#fafafa',
            width: '100%',
            fontFamily: 'inherit',
            color: value ? '#000' : '#999',
            boxSizing: 'border-box',
            outline: 'none',
          }}
        />
        {value ? (
          <TouchableOpacity
            style={styles.clearBtn}
            onPress={() => onChange('')}
            testID={testID ? `${testID}-clear` : undefined}
          >
            <Ionicons name="close-circle" size={18} color="#999" />
          </TouchableOpacity>
        ) : null}
      </View>
    );
  }

  // Native iOS / Android
  return (
    <>
      <TouchableOpacity
        style={styles.nativeInput}
        onPress={() => {
          if (disabled) return;
          setTempDate(isoToDate(value));
          setShowPicker(true);
        }}
        testID={testID}
        disabled={disabled}
      >
        <Text style={{ color: value ? '#000' : '#999', fontSize: 15 }}>
          {value ? formatDisplay(value) : placeholder}
        </Text>
        <Ionicons name="calendar-outline" size={18} color="#666" />
      </TouchableOpacity>

      {Platform.OS === 'android' && showPicker && (
        <DateTimePicker
          value={isoToDate(value)}
          mode="date"
          display="default"
          minimumDate={minimumDate}
          maximumDate={maximumDate}
          onChange={(_, selected) => {
            setShowPicker(false);
            if (selected) onChange(dateToIso(selected));
          }}
        />
      )}

      {Platform.OS === 'ios' && (
        <Modal visible={showPicker} transparent animationType="fade">
          <View style={styles.iosOverlay}>
            <View style={styles.iosSheet}>
              <DateTimePicker
                value={tempDate}
                mode="date"
                display="inline"
                minimumDate={minimumDate}
                maximumDate={maximumDate}
                onChange={(_, selected) => {
                  if (selected) setTempDate(selected);
                }}
                style={{ backgroundColor: '#fff' }}
              />
              <View style={styles.iosActions}>
                <TouchableOpacity onPress={() => setShowPicker(false)}>
                  <Text style={styles.iosCancel}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => {
                    onChange(dateToIso(tempDate));
                    setShowPicker(false);
                  }}
                >
                  <Text style={styles.iosOk}>OK</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>
      )}
    </>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: 'relative',
    width: '100%',
  },
  clearBtn: {
    position: 'absolute',
    right: 28,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  nativeInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 10,
    backgroundColor: '#fafafa',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  iosOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 24,
  },
  iosSheet: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 12,
  },
  iosActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingTop: 12,
  },
  iosCancel: { color: '#d32f2f', fontWeight: '600', fontSize: 16 },
  iosOk: { color: '#6a1b9a', fontWeight: '700', fontSize: 16 },
});

export default DateField;
